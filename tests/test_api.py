from fastapi.testclient import TestClient
from api.main import app
import api.main as api_main
from config import settings
client=TestClient(app)
def auth(): return {"Authorization":f"Bearer {settings.api_token}"}
def test_health(): assert client.get("/health").json()["status"]=="ok"
def test_database_readiness():
    response=client.get("/health/ready")
    assert response.status_code==200 and response.json()=={"status":"ready","database":"ok"}
def test_auth_required(): assert client.get("/api/analytics/it").status_code==401
def test_analytics_and_investigation():
    e=client.get("/api/analytics/ecommerce",headers=auth()); assert e.status_code==200 and e.json()["orders"]>=1000
    r=client.post("/api/chat",headers=auth(),json={"query":"Summarize return policy and trends","domain":"ecommerce"}); assert r.status_code==200 and "SIMULATED" in r.json()["answer"]

def test_rag_health_and_ask(monkeypatch):
    health=client.get("/api/rag/health",headers=auth())
    assert health.status_code==200 and health.json()["vector_store"]=="faiss"
    monkeypatch.setattr(api_main,"ask_question",lambda *a,**k:{"answer":"grounded","sources":[],"retrieval_count":0,"provider":"demo","demo_mode":True})
    response=client.post("/api/rag/ask",headers=auth(),json={"question":"What do documents say?","domain":"it"})
    assert response.status_code==200 and response.json()["provider"]=="demo"

def test_rag_upload_validation_and_success(monkeypatch,tmp_path):
    from config import settings
    monkeypatch.setattr(settings,"upload_dir",str(tmp_path))
    monkeypatch.setattr(api_main.vector_store,"has_document",lambda _:False)
    monkeypatch.setattr(api_main,"ingest_document",lambda path,category,document_name:{"document_name":document_name,"chunks":1,"category":category or "general"})
    response=client.post("/api/rag/upload",headers=auth(),files={"file":("notes.txt",b"Useful IT runbook.","text/plain")},data={"category":"it_documentation"})
    assert response.status_code==200 and response.json()["chunks"]==1
    unsupported=client.post("/api/rag/upload",headers=auth(),files={"file":("bad.docx",b"x","application/octet-stream")})
    assert unsupported.status_code==415
    monkeypatch.setattr(api_main.vector_store,"has_document",lambda _:True)
    duplicate=client.post("/api/rag/upload",headers=auth(),files={"file":("notes.txt",b"Useful IT runbook.","text/plain")})
    assert duplicate.status_code==409
