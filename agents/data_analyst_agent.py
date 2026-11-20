"""Data analyst backed exclusively by discovered Database MCP tools."""
from config import settings
from mcp_clients.tool_registry import invoke_agent_tool_sync

def _payload(result: dict) -> dict:
    value = result.get("structuredContent")
    if isinstance(value, dict) and "result" in value and isinstance(value["result"], dict): return value["result"]
    return value if isinstance(value, dict) else {"ok": False, "error": {"message": "MCP returned no structured object."}}

def analyze(domain: str, query: str = "") -> dict:
    if domain == "ecommerce":
        stats = _payload(invoke_agent_tool_sync("data_analyst", "get_return_statistics", {}, timeout=settings.mcp_timeout_seconds))
        inventory = _payload(invoke_agent_tool_sync("data_analyst", "get_inventory_status", {"limit": 100}, timeout=settings.mcp_timeout_seconds))
        if not stats.get("ok", True): raise RuntimeError("Database MCP return statistics unavailable")
        items = inventory.get("items", [])
        return {"query_focus": query, "source": "Database MCP server", "orders": stats.get("orders", 0),
                "returns": stats.get("returns", 0), "return_rate": stats.get("return_rate", 0),
                "complaints": stats.get("complaints", 0), "low_inventory_products": stats.get("low_inventory_products", len(items)),
                "low_inventory_items": items}
    stats = _payload(invoke_agent_tool_sync("data_analyst", "get_support_ticket_statistics", {}, timeout=settings.mcp_timeout_seconds))
    if not stats.get("ok", True): raise RuntimeError("Database MCP support statistics unavailable")
    return {"query_focus": query, "source": "Database MCP server", "open_tickets": stats.get("open_tickets", 0),
            "critical_tickets": stats.get("critical_tickets", 0), "critical_incidents": stats.get("critical_incidents", 0),
            "ticket_categories": stats.get("ticket_categories", [])}
