import json
from fastapi.testclient import TestClient
from api.main import app
from config import settings
from database.connection import SessionLocal, Base, engine
from database.models import Approval, AuditEvent, Ticket
import agents.execution_agent as execution_agent
import uuid

client=TestClient(app)
Base.metadata.create_all(engine)

def manager_token(monkeypatch):
    monkeypatch.setattr(settings,"admin_bootstrap_key","approval-test-key")
    name="approver_"+uuid.uuid4().hex[:10]
    client.post("/api/auth/register",json={"username":name,"password":"Long-Passphrase-2026!","role":"manager","admin_bootstrap_key":"approval-test-key"})
    return client.post("/api/auth/login",json={"username":name,"password":"Long-Passphrase-2026!"}).json()["access_token"]

def add_approval():
    db=SessionLocal()
    try:
        row=Approval(request="test action",action="update_ticket_status",payload=json.dumps({"type":"update_ticket_status","ticket_id":1,"status":"resolved"}),status="pending")
        db.add(row);db.commit();db.refresh(row);return row.id
    finally:db.close()

def test_approval_rejects_without_execution_and_audits(monkeypatch):
    token=manager_token(monkeypatch); approval_id=add_approval()
    monkeypatch.setattr(execution_agent,"execute_approved",lambda *a,**k: (_ for _ in ()).throw(AssertionError("must not execute")))
    response=client.post(f"/api/approvals/{approval_id}/reject",headers={"Authorization":f"Bearer {token}"})
    assert response.status_code==200 and response.json()["status"]=="rejected"
    db=SessionLocal()
    try:
        assert db.get(Approval,approval_id).status=="rejected"
        assert db.query(AuditEvent).filter_by(workflow_id=f"approval:{approval_id}",approval_decision="rejected").count()==1
    finally:db.close()

def test_approved_action_executes_once_and_records_audit(monkeypatch):
    token=manager_token(monkeypatch); approval_id=add_approval(); calls=[]
    monkeypatch.setattr(execution_agent,"execute_approved",lambda *a,**k: calls.append(k["approval_id"]) or {"status":"executed"})
    headers={"Authorization":f"Bearer {token}"}
    first=client.post(f"/api/approvals/{approval_id}/approve",headers=headers)
    duplicate=client.post(f"/api/approvals/{approval_id}/approve",headers=headers)
    assert first.status_code==200 and duplicate.status_code==409 and calls==[approval_id]
    db=SessionLocal()
    try:
        event=db.query(AuditEvent).filter_by(workflow_id=f"approval:{approval_id}",approval_decision="approved").one()
        assert event.execution_result and event.request_id
    finally:db.close()

def test_approved_ticket_uses_real_mcp_execution(monkeypatch):
    token=manager_token(monkeypatch)
    title="Approved MCP ticket "+uuid.uuid4().hex[:8]
    db=SessionLocal()
    try:
        row=Approval(request="approved MCP ticket",action="create_it_ticket",payload=json.dumps({
            "type":"create_it_ticket","title":title,"description":"Ticket created through approved MCP protocol call.","severity":"low"}),status="pending")
        db.add(row);db.commit();db.refresh(row);approval_id=row.id
    finally:db.close()
    response=client.post(f"/api/approvals/{approval_id}/approve",headers={"Authorization":f"Bearer {token}"})
    assert response.status_code==200
    assert response.json()["execution"]["status"]=="executed"
    assert response.json()["execution"]["ticket_id"]
    db=SessionLocal()
    try: assert db.query(Ticket).filter_by(title=title).count()==1
    finally:db.close()
