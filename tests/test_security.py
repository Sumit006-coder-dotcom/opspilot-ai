from fastapi.testclient import TestClient
from api.main import app
from config import settings
from database.connection import Base, engine

client=TestClient(app)
Base.metadata.create_all(engine)

def test_auth_required_and_cors_headers():
    assert client.get("/api/tickets").status_code==401
    response=client.options("/api/analytics/it",headers={"Origin":"http://localhost:8501","Access-Control-Request-Method":"GET"})
    assert response.status_code==200
    assert response.headers.get("access-control-allow-origin")=="http://localhost:8501"

def test_upload_rejects_unsupported_file_before_writing():
    response=client.post("/api/rag/upload",headers={"Authorization":f"Bearer {settings.api_token}"},files={"file":("bad.exe",b"x","application/octet-stream")})
    assert response.status_code==415

def test_openapi_exposes_bearer_security_scheme():
    schema=client.get("/openapi.json").json()
    assert "HTTPBearer" in schema["components"]["securitySchemes"]
