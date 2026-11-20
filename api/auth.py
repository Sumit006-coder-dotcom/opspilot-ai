"""Password hashing and compact HS256 JWT helpers; no plaintext credentials are stored."""
from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from config import settings
from database.connection import get_db
from database.models import User

ROLES = {"admin", "manager", "analyst", "viewer"}
ITERATIONS = 310_000

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${_b64(salt)}${_b64(key)}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, expected = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256": return False
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(iterations))
        return hmac.compare_digest(_b64(key), expected)
    except (ValueError, TypeError): return False

def _b64(value: bytes) -> str: return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
def _unb64(value: str) -> bytes: return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def create_access_token(user: User) -> str:
    header = _b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",", ":")).encode())
    now = int(time.time())
    payload = _b64(json.dumps({"sub":str(user.id),"username":user.username,"role":user.role,
        "iat":now,"exp":now + max(1, settings.jwt_expire_minutes) * 60}, separators=(",", ":")).encode())
    body = f"{header}.{payload}"
    signature = hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"

def decode_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        if json.loads(_unb64(header)).get("alg") != "HS256": raise ValueError()
        body = f"{header}.{payload}"
        expected = _b64(hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): raise ValueError()
        claims = json.loads(_unb64(payload))
        if int(claims.get("exp", 0)) <= int(time.time()): raise ValueError()
        return claims
    except Exception as exc: raise HTTPException(401, "Invalid or expired bearer token") from exc

bearer_scheme=HTTPBearer(auto_error=False)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), db: Session = Depends(get_db)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Valid bearer token required", headers={"WWW-Authenticate":"Bearer"})
    token = credentials.credentials.strip()
    # Compatibility for existing local scripts and demo clients. Disable by setting a non-demo API_TOKEN.
    if settings.demo_mode and settings.api_token and hmac.compare_digest(token, settings.api_token):
        return {"id":0,"username":"demo-system","role":"admin","legacy":True}
    claims = decode_access_token(token)
    user = db.get(User, int(claims.get("sub", 0)))
    if not user or user.role != claims.get("role"):
        raise HTTPException(401, "Invalid or expired bearer token")
    return user

def require_roles(*roles: str):
    allowed = {role.lower() for role in roles}
    def dependency(user=Depends(current_user)):
        role = user["role"] if isinstance(user, dict) else user.role
        if role not in allowed: raise HTTPException(403, "Insufficient role")
        return user
    return dependency

