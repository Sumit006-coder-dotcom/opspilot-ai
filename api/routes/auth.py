from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from config import settings
from database.connection import get_db
from database.models import User
from api.auth import ROLES, create_access_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(default="analyst", pattern=r"^(?i:admin|manager|analyst|viewer)$")
    admin_bootstrap_key: str | None = Field(default=None, max_length=256)

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    username = req.username.strip()
    if db.query(User).filter(func.lower(User.username) == username.lower()).first():
        raise HTTPException(409, "Username is already registered")
    requested = req.role.lower()
    existing = db.query(User).count()
    # First user is an analyst. Privileged roles require an explicit bootstrap secret.
    role = "analyst"
    if requested in {"admin", "manager"}:
        if not settings.admin_bootstrap_key or req.admin_bootstrap_key is None or not __import__("hmac").compare_digest(req.admin_bootstrap_key, settings.admin_bootstrap_key):
            raise HTTPException(403, "Privileged role requires administrator bootstrap authorization")
        role = requested
    user = User(username=username, password_hash=hash_password(req.password), role=role)
    db.add(user)
    try: db.commit(); db.refresh(user)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Username is already registered")
    return {"id":user.id,"username":user.username,"role":user.role}

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.username) == req.username.strip().lower()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password", headers={"WWW-Authenticate":"Bearer"})
    return {"access_token":create_access_token(user),"token_type":"bearer","expires_in":max(1,settings.jwt_expire_minutes)*60}

@router.get("/me")
def me(user=Depends(current_user)):
    if isinstance(user, dict): return {"id":user["id"],"username":user["username"],"role":user["role"]}
    return {"id":user.id,"username":user.username,"role":user.role}
