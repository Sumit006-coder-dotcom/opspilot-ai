"""IT operations tools exposed through the official MCP protocol."""
from __future__ import annotations
import logging
from typing import Any
from sqlalchemy import or_
from mcp_servers.runtime import create_server, serve
from mcp_servers.security import authorize_approved_write, MCPAuthorizationError, tool_error, audit_tool
from database.connection import SessionLocal
from database.models import Ticket, Incident

logger = logging.getLogger("operlynt.mcp.it")
mcp = create_server("operlynt-it-operations")

@mcp.tool(description="Search IT ticket titles and descriptions. Limit must be between 1 and 100.", structured_output=True)
def search_it_tickets(query: str, limit: int = 20) -> dict[str, Any]:
    clean = query.strip()
    if not 2 <= len(clean) <= 500: return {"ok": False, "error": {"code": "invalid_input", "message": "query must contain 2 to 500 characters."}}
    if not 1 <= limit <= 100: return {"ok": False, "error": {"code": "invalid_input", "message": "limit must be between 1 and 100."}}
    db = SessionLocal()
    try:
        rows = db.query(Ticket).filter(or_(Ticket.title.ilike(f"%{clean[:120]}%"), Ticket.description.ilike(f"%{clean[:120]}%"))).order_by(Ticket.id.desc()).limit(limit).all()
        return {"ok": True, "tickets": [{"id": r.id, "title": r.title, "category": r.category, "severity": r.severity, "status": r.status, "description": r.description} for r in rows]}
    except Exception as exc:
        logger.exception("search_it_tickets failed")
        return {"ok": False, "error": {"code": "database_error", "message": f"Ticket search failed ({type(exc).__name__})."}}
    finally: db.close()

@mcp.tool(description="Get one incident by its integer ID. Read-only lookup.", structured_output=True)
def get_incident_details(incident_id: int) -> dict[str, Any]:
    if incident_id < 1: return {"ok": False, "error": {"code": "invalid_input", "message": "incident_id must be positive."}}
    db = SessionLocal()
    try:
        r = db.get(Incident, incident_id)
        return {"ok": True, "incident": None if not r else {"id": r.id, "title": r.title, "severity": r.severity, "status": r.status, "service": r.service, "description": r.description}}
    except Exception as exc:
        logger.exception("get_incident_details failed")
        return {"ok": False, "error": {"code": "database_error", "message": f"Incident lookup failed ({type(exc).__name__})."}}
    finally: db.close()

@mcp.tool(description="Create an IT support ticket only for a matching approved request.", structured_output=True)
def create_it_ticket(title: str, description: str, severity: str, approval_id: int, authorization_token: str) -> dict[str, Any]:
    title, description = title.strip(), description.strip()
    if not 3 <= len(title) <= 200 or not 3 <= len(description) <= 2000 or severity not in {"low", "medium", "high", "critical"}:
        return {"ok": False, "error": {"code": "invalid_input", "message": "title, description, or severity is invalid."}}
    expected = {"title": title, "description": description, "severity": severity}
    try:
        authorize_approved_write(authorization_token, approval_id, "create_it_ticket", expected)
        db = SessionLocal()
        try:
            ticket = Ticket(title=title, description=description, severity=severity, category="other", status="open")
            db.add(ticket); db.commit(); db.refresh(ticket); ticket_id = ticket.id
        finally: db.close()
        audit_tool("create_it_ticket", "success", f"approval_id={approval_id}; ticket_id={ticket_id}")
        return {"ok": True, "status": "created", "approval_id": approval_id, "ticket_id": ticket_id}
    except MCPAuthorizationError as exc:
        audit_tool("create_it_ticket", "rejected", f"approval_id={approval_id}; code={exc.code}"); return tool_error(exc)
    except Exception as exc:
        logger.exception("create_it_ticket failed")
        return {"ok": False, "error": {"code": "execution_error", "message": f"Ticket creation failed ({type(exc).__name__})."}}

@mcp.tool(description="Record an incident escalation only for a matching approved request.", structured_output=True)
def escalate_it_incident(incident_id: int, reason: str, approval_id: int, authorization_token: str) -> dict[str, Any]:
    reason = reason.strip()
    if incident_id < 1 or not 3 <= len(reason) <= 1000:
        return {"ok": False, "error": {"code": "invalid_input", "message": "incident_id or reason is invalid."}}
    try:
        authorize_approved_write(authorization_token, approval_id, "escalate_it_incident", {"incident_id": incident_id})
        db = SessionLocal()
        try:
            if not db.get(Incident, incident_id): return {"ok": False, "error": {"code": "not_found", "message": "Incident not found."}}
        finally: db.close()
        audit_tool("escalate_it_incident", "success", f"approval_id={approval_id}; incident_id={incident_id}; reason={reason[:300]}")
        return {"ok": True, "status": "escalated", "approval_id": approval_id, "incident_id": incident_id}
    except MCPAuthorizationError as exc:
        audit_tool("escalate_it_incident", "rejected", f"approval_id={approval_id}; code={exc.code}"); return tool_error(exc)
    except Exception as exc:
        logger.exception("escalate_it_incident failed")
        return {"ok": False, "error": {"code": "execution_error", "message": f"Escalation failed ({type(exc).__name__})."}}

@mcp.tool(description="Change a ticket status only for a matching approved request.", structured_output=True)
def update_ticket_status(ticket_id: int, status: str, approval_id: int, authorization_token: str) -> dict[str, Any]:
    if ticket_id < 1 or status not in {"open", "in_progress", "resolved"}:
        return {"ok": False, "error": {"code": "invalid_input", "message": "ticket_id or status is invalid."}}
    try:
        authorize_approved_write(authorization_token, approval_id, "update_ticket_status", {"ticket_id": ticket_id, "status": status})
        db = SessionLocal()
        try:
            ticket = db.get(Ticket, ticket_id)
            if not ticket: return {"ok": False, "error": {"code": "not_found", "message": "Ticket not found."}}
            ticket.status = status; db.commit()
        finally: db.close()
        audit_tool("update_ticket_status", "success", f"approval_id={approval_id}; ticket_id={ticket_id}; status={status}")
        return {"ok": True, "status": "updated", "approval_id": approval_id, "ticket_id": ticket_id, "ticket_status": status}
    except MCPAuthorizationError as exc:
        audit_tool("update_ticket_status", "rejected", f"approval_id={approval_id}; code={exc.code}"); return tool_error(exc)
    except Exception as exc:
        logger.exception("update_ticket_status failed")
        return {"ok": False, "error": {"code": "execution_error", "message": f"Ticket update failed ({type(exc).__name__})."}}

if __name__ == "__main__": serve(mcp)
