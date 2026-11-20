import uuid
from fastapi.testclient import TestClient
from api.main import app
from config import settings
from database.connection import Base, engine

client=TestClient(app)
Base.metadata.create_all(engine)

def manager_headers(monkeypatch):
    monkeypatch.setattr(settings,"admin_bootstrap_key","test-bootstrap-secret")
    username="manager_"+uuid.uuid4().hex[:10]
    registered=client.post("/api/auth/register",json={"username":username,"password":"Long-Passphrase-2026!","role":"manager","admin_bootstrap_key":"test-bootstrap-secret"})
    assert registered.status_code==201
    token=client.post("/api/auth/login",json={"username":username,"password":"Long-Passphrase-2026!"}).json()["access_token"]
    return {"Authorization":f"Bearer {token}"}

def test_required_routes_and_authentication(monkeypatch):
    assert app.title=="Operlynt"
    assert client.get("/health").status_code==200
    assert client.get("/api/analytics/ecommerce").status_code==401
    headers=manager_headers(monkeypatch)
    ecommerce=client.get("/api/analytics/ecommerce",headers=headers)
    assert ecommerce.status_code==200 and "product_return_distribution" in ecommerce.json() and "complaint_trends" in ecommerce.json()
    it=client.get("/api/analytics/it",headers=headers)
    assert it.status_code==200 and "ticket_severity" in it.json() and "ticket_trends" in it.json()
    assert client.get("/api/analytics/products",headers=headers).status_code==200
    assert client.get("/api/analytics/complaints",headers=headers).status_code==200
    assert client.get("/api/tickets",headers=headers).status_code==200
    assert client.get("/api/approvals",headers=headers).status_code==200
    assert client.get("/api/rag/documents",headers=headers).status_code==200
    assert client.get("/api/agents/activity",headers=headers).status_code==200
    assert client.get("/openapi.json").status_code==200

def test_viewer_cannot_create_sensitive_action(monkeypatch):
    username="viewer_"+uuid.uuid4().hex[:10]
    client.post("/api/auth/register",json={"username":username,"password":"Long-Passphrase-2026!","role":"viewer"})
    token=client.post("/api/auth/login",json={"username":username,"password":"Long-Passphrase-2026!"}).json()["access_token"]
    response=client.post("/api/tickets",headers={"Authorization":f"Bearer {token}"},json={"title":"System issue","description":"A sufficiently detailed description","category":"network"})
    assert response.status_code==403
