"""Authorization and audit helpers for write-capable MCP tools."""
from __future__ import annotations
import hmac
import json
import logging
from database.connection import SessionLocal
from database.models import AgentLog, Approval
from config import settings

log = logging.getLogger("operlynt.mcp.security")

class MCPAuthorizationError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)

def authorize_approved_write(authorization_token: str | None, approval_id: int | None,
                             action: str, expected: dict) -> dict:
    if not authorization_token or not hmac.compare_digest(authorization_token, settings.api_token):
        raise MCPAuthorizationError("unauthorized", "Valid Operlynt authorization is required.")
    if not approval_id:
        raise MCPAuthorizationError("approval_required", "A resolved approval ID is required.")
    db = SessionLocal()
    try:
        approval = db.get(Approval, approval_id)
        if not approval or approval.status != "approved":
            raise MCPAuthorizationError("approval_required", "The referenced operation is not approved.")
        if approval.action != action:
            raise MCPAuthorizationError("approval_mismatch", "The approval does not authorize this operation.")
        payload = json.loads(approval.payload or "{}")
        if any(payload.get(key) != value for key, value in expected.items()):
            raise MCPAuthorizationError("approval_mismatch", "The requested operation differs from the approved payload.")
        return payload
    finally:
        db.close()

def tool_error(exc: MCPAuthorizationError) -> dict:
    log.warning("MCP write rejected: %s", exc.code)
    return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

def audit_tool(name: str, status: str, detail: str) -> None:
    db = SessionLocal()
    try:
        db.add(AgentLog(agent="mcp_execution" if status == "success" else "mcp_security",
                        tool=name, status=status, detail=detail[:1000]))
        db.commit()
    finally:
        db.close()
