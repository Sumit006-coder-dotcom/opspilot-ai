"""E-commerce specialist using discovered E-commerce MCP tools."""
from __future__ import annotations
import re
from config import settings
from mcp_clients.tool_registry import invoke_agent_tool_sync

def investigate(query: str) -> dict:
    calls = []
    match = re.search(r"\border(?:\s+id)?\s*#?\s*(\d+)\b", query, re.I)
    if match:
        calls.append(("get_order_details", {"order_id": int(match.group(1))}))
    product = re.search(r"\bproduct(?:\s+id)?\s*#?\s*(\d+)\b", query, re.I)
    if product:
        calls.append(("get_product_return_rate", {"product_id": int(product.group(1))}))
    seller = re.search(r"\bseller(?:\s+id)?\s*#?\s*(\d+)\b", query, re.I)
    if seller:
        calls.append(("get_seller_performance", {"seller_id": int(seller.group(1))}))
    evidence = {}
    for name, args in calls:
        response = invoke_agent_tool_sync("ecommerce", name, args, timeout=settings.mcp_timeout_seconds)
        evidence[name] = response.get("structuredContent", {})
    return {"domain": "ecommerce", "query_focus": query, "mcp_server": "ecommerce",
            "mcp_tools_used": [name for name, _ in calls], "record_evidence": evidence,
            "responsibility": "Investigates identified orders, product return rates, and seller performance using e-commerce MCP records.",
            "next_input_hint": None if calls else "Include an order ID, product ID, or seller ID for a record-specific investigation."}
