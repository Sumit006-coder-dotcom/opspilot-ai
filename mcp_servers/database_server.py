"""Read-only database tools exposed through the official MCP protocol."""
from __future__ import annotations
import logging
from typing import Any
from sqlalchemy import func
from mcp_servers.runtime import create_server, serve
from database.connection import SessionLocal
from database.models import Product, Order, Complaint, Ticket, Incident, Inventory

logger = logging.getLogger("operlynt.mcp.database")
mcp = create_server("operlynt-database")

def _failure(tool: str, exc: Exception) -> dict:
    logger.exception("Database MCP tool %s failed", tool)
    return {"ok": False, "error": {"code": "database_error", "message": f"{tool} could not complete ({type(exc).__name__})."}}

@mcp.tool(description="Get one product by its integer database ID. Read-only lookup.", structured_output=True)
def get_product_details(product_id: int) -> dict[str, Any]:
    if product_id < 1: return {"ok": False, "error": {"code": "invalid_input", "message": "product_id must be positive."}}
    db = SessionLocal()
    try:
        p = db.get(Product, product_id)
        return {"ok": True, "product": None if p is None else {"id": p.id, "name": p.name, "category": p.category, "price": p.price}}
    except Exception as exc: return _failure("get_product_details", exc)
    finally: db.close()

@mcp.tool(description="Return order count, returned order count, return rate, complaints, and low-stock product counts.", structured_output=True)
def get_return_statistics() -> dict[str, Any]:
    db = SessionLocal()
    try:
        orders = db.query(Order).count(); returned = db.query(Order).filter_by(returned=True).count()
        complaints = db.query(Complaint).count(); low = db.query(Inventory).filter(Inventory.quantity < Inventory.reorder_point).count()
        return {"ok": True, "orders": orders, "returns": returned, "return_rate": round(returned / max(orders, 1) * 100, 2), "complaints": complaints, "low_inventory_products": low}
    except Exception as exc: return _failure("get_return_statistics", exc)
    finally: db.close()

@mcp.tool(description="List products below their reorder points. Limit must be between 1 and 100.", structured_output=True)
def get_inventory_status(limit: int = 100) -> dict[str, Any]:
    if not 1 <= limit <= 100: return {"ok": False, "error": {"code": "invalid_input", "message": "limit must be between 1 and 100."}}
    db = SessionLocal()
    try:
        rows = db.query(Inventory, Product).join(Product).filter(Inventory.quantity < Inventory.reorder_point).order_by(Inventory.quantity).limit(limit).all()
        return {"ok": True, "items": [{"product_id": p.id, "product": p.name, "quantity": i.quantity, "reorder_point": i.reorder_point} for i, p in rows]}
    except Exception as exc: return _failure("get_inventory_status", exc)
    finally: db.close()

@mcp.tool(description="Return open, critical, incident, and category counts for IT support records.", structured_output=True)
def get_support_ticket_statistics() -> dict[str, Any]:
    db = SessionLocal()
    try:
        return {"ok": True, "open_tickets": db.query(Ticket).filter(Ticket.status != "resolved").count(),
                "critical_tickets": db.query(Ticket).filter(Ticket.severity == "critical", Ticket.status != "resolved").count(),
                "critical_incidents": db.query(Incident).filter(Incident.severity == "critical", Incident.status != "resolved").count(),
                "ticket_categories": [{"category": c, "count": n} for c, n in db.query(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category).all()]}
    except Exception as exc: return _failure("get_support_ticket_statistics", exc)
    finally: db.close()

@mcp.tool(description="Search customer complaints by text. Limit must be between 1 and 100.", structured_output=True)
def search_customer_complaints(query: str, limit: int = 20) -> dict[str, Any]:
    clean = query.strip()
    if not 2 <= len(clean) <= 500: return {"ok": False, "error": {"code": "invalid_input", "message": "query must contain 2 to 500 characters."}}
    if not 1 <= limit <= 100: return {"ok": False, "error": {"code": "invalid_input", "message": "limit must be between 1 and 100."}}
    db = SessionLocal()
    try:
        rows = db.query(Complaint).filter(Complaint.text.ilike(f"%{clean[:120]}%")).order_by(Complaint.id.desc()).limit(limit).all()
        return {"ok": True, "records": [{"id": c.id, "category": c.category, "text": c.text, "order_id": c.order_id} for c in rows]}
    except Exception as exc: return _failure("search_customer_complaints", exc)
    finally: db.close()

if __name__ == "__main__": serve(mcp)
