"""E-commerce operational tools exposed through the official MCP protocol."""
from __future__ import annotations
import logging
from typing import Any
from mcp_servers.runtime import create_server, serve
from mcp_servers.security import authorize_approved_write, MCPAuthorizationError, tool_error, audit_tool
from database.connection import SessionLocal
from database.models import Order, Product, Seller, Ticket, Approval

logger = logging.getLogger("operlynt.mcp.ecommerce")
mcp = create_server("operlynt-ecommerce")

@mcp.tool(description="Get order, product, and return details by order ID. Read-only lookup.", structured_output=True)
def get_order_details(order_id: int) -> dict[str, Any]:
    if order_id < 1: return {"ok": False, "error": {"code": "invalid_input", "message": "order_id must be positive."}}
    db = SessionLocal()
    try:
        row = db.get(Order, order_id)
        if not row: return {"ok": True, "order": None}
        product = db.get(Product, row.product_id)
        return {"ok": True, "order": {"id": row.id, "status": row.status, "returned": row.returned,
                "product_id": row.product_id, "product": product.name if product else None, "seller_id": row.seller_id}}
    except Exception as exc:
        logger.exception("get_order_details failed")
        return {"ok": False, "error": {"code": "database_error", "message": f"Lookup failed ({type(exc).__name__})."}}
    finally: db.close()

@mcp.tool(description="Get seller rating and order volume by seller ID. Read-only lookup.", structured_output=True)
def get_seller_performance(seller_id: int) -> dict[str, Any]:
    if seller_id < 1: return {"ok": False, "error": {"code": "invalid_input", "message": "seller_id must be positive."}}
    db = SessionLocal()
    try:
        seller = db.get(Seller, seller_id)
        if not seller: return {"ok": True, "seller": None}
        return {"ok": True, "seller": {"id": seller.id, "name": seller.name, "rating": seller.rating,
                "orders": db.query(Order).filter_by(seller_id=seller_id).count()}}
    except Exception as exc:
        logger.exception("get_seller_performance failed")
        return {"ok": False, "error": {"code": "database_error", "message": f"Lookup failed ({type(exc).__name__})."}}
    finally: db.close()

@mcp.tool(description="Calculate order and return counts for one product ID. Read-only lookup.", structured_output=True)
def get_product_return_rate(product_id: int) -> dict[str, Any]:
    if product_id < 1: return {"ok": False, "error": {"code": "invalid_input", "message": "product_id must be positive."}}
    db = SessionLocal()
    try:
        total = db.query(Order).filter_by(product_id=product_id).count()
        returned = db.query(Order).filter_by(product_id=product_id, returned=True).count()
        return {"ok": True, "product_id": product_id, "orders": total, "returns": returned,
                "return_rate_pct": round(returned / max(total, 1) * 100, 2)}
    except Exception as exc:
        logger.exception("get_product_return_rate failed")
        return {"ok": False, "error": {"code": "database_error", "message": f"Lookup failed ({type(exc).__name__})."}}
    finally: db.close()

@mcp.tool(description="Record an approved e-commerce escalation. Requires a matching approved operation and authorization token.", structured_output=True)
def create_ecommerce_escalation(reason: str, product_id: int, approval_id: int, authorization_token: str) -> dict[str, Any]:
    clean = reason.strip()
    if not clean or len(clean) > 1000 or product_id < 1:
        return {"ok": False, "error": {"code": "invalid_input", "message": "reason and positive product_id are required."}}
    try:
        authorize_approved_write(authorization_token, approval_id, "ecommerce_escalation", {"product_id": product_id})
        audit_tool("create_ecommerce_escalation", "success", f"approval_id={approval_id}; product_id={product_id}; reason={clean[:300]}")
        return {"ok": True, "status": "executed", "approval_id": approval_id, "product_id": product_id}
    except MCPAuthorizationError as exc:
        audit_tool("create_ecommerce_escalation", "rejected", f"approval_id={approval_id}; code={exc.code}")
        return tool_error(exc)
    except Exception as exc:
        logger.exception("create_ecommerce_escalation failed")
        return {"ok": False, "error": {"code": "execution_error", "message": f"Escalation failed ({type(exc).__name__})."}}

if __name__ == "__main__": serve(mcp)
