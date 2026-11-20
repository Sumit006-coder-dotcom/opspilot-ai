"""Approval-gated business operation preparation and execution."""
from __future__ import annotations
import json
from config import settings
from database.connection import SessionLocal
from database.models import Approval
from mcp_clients.tool_registry import invoke_agent_tool_sync

def prepare(request: str, action: dict | None = None) -> dict:
    action = action or {"type": "review_recommendations"}
    return {"request": request, "type": action.get("type", "operational_action"), "payload": action,
            "requires_human_approval": True, "status": "awaiting_approval"}

def create_approval(request: str, action: dict, thread_id: str, user_id: str) -> dict:
    db = SessionLocal()
    try:
        row = Approval(request=request, action=action.get("type", "operational_action"),
                       payload=json.dumps({**action, "thread_id": thread_id, "user_id": user_id}), status="pending")
        db.add(row); db.commit(); db.refresh(row)
        return {"approval_id": row.id, "status": "pending", "action": action}
    finally: db.close()

def execute_approved(action: dict, approval_id: int | None = None) -> dict:
    """Dispatch approved operations through the real IT/E-commerce MCP servers."""
    kind = action.get("type")
    if not approval_id: return {"status": "error", "error": "approval_id_required", "action": kind}
    if kind in {"update_ticket_status", "create_it_ticket", "escalate_it_incident"}:
        tool = kind; server_agent = "execution"
        args = {key: action[key] for key in ("ticket_id", "status", "title", "description", "severity", "incident_id", "reason") if key in action}
    elif kind in {"ecommerce_escalation", "create_ecommerce_escalation"}:
        tool = "create_ecommerce_escalation"; server_agent = "execution"
        args = {"product_id": action.get("product_id"), "reason": action.get("reason", "Approved e-commerce escalation")}
    else: return {"status": "error", "error": "unsupported_action", "action": kind}
    args.update({"approval_id": approval_id, "authorization_token": settings.api_token})
    response = invoke_agent_tool_sync(server_agent, tool, args, timeout=settings.mcp_timeout_seconds, authorized_execution=True)
    result = response.get("structuredContent", {})
    if not isinstance(result, dict): result = {"ok": False, "error": "invalid_structured_response"}
    if result.get("ok"):
        return {**result, "tool_status": result.get("status"), "status": "executed"}
    error = result.get("error", {})
    return {"status": "rejected", "error": error.get("code", "execution_error"), "message": error.get("message", "MCP execution was rejected.")}

# Phase 1 compatibility: this function only creates a pending approval.
def propose(request: str, action: dict | None = None) -> dict:
    return create_approval(request, action or {"type": "operational_action"}, "legacy", "legacy")
