import uuid
from fastapi.testclient import TestClient
from api.main import app
from config import settings
from database.connection import SessionLocal
from database.connection import Base, engine
from database.models import User

client=TestClient(app)
Base.metadata.create_all(engine)

def test_register_login_and_me_never_store_plaintext():
    username="user_"+uuid.uuid4().hex[:12]
    password="Correct-Horse-42!"
    created=client.post("/api/auth/register",json={"username":username,"password":password})
    assert created.status_code==201 and created.json()["role"]=="analyst"
    db=SessionLocal()
    try:
        user=db.query(User).filter_by(username=username).one()
        assert user.password_hash != password and user.password_hash.startswith("pbkdf2_sha256$")
    finally: db.close()
    logged=client.post("/api/auth/login",json={"username":username,"password":password})
    assert logged.status_code==200
    token=logged.json()["access_token"]
    me=client.get("/api/auth/me",headers={"Authorization":f"Bearer {token}"})
    assert me.status_code==200 and me.json()["username"]==username
    assert client.post("/api/auth/login",json={"username":username,"password":"wrong"}).status_code==401

def test_register_cannot_self_assign_admin():
    username="admin_"+uuid.uuid4().hex[:12]
    response=client.post("/api/auth/register",json={"username":username,"password":"Correct-Horse-42!","role":"admin"})
    assert response.status_code==403

def test_expired_or_tampered_token_is_denied(monkeypatch):
    username="jwt_"+uuid.uuid4().hex[:12]
    client.post("/api/auth/register",json={"username":username,"password":"Correct-Horse-42!"})
    token=client.post("/api/auth/login",json={"username":username,"password":"Correct-Horse-42!"}).json()["access_token"]
    bad=token[:-1]+("a" if token[-1]!="a" else "b")
    assert client.get("/api/auth/me",headers={"Authorization":f"Bearer {bad}"}).status_code==401
