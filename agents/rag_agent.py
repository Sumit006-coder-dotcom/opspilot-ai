"""Policy and technical documentation retrieval via Document MCP tools."""
from config import settings
from mcp_clients.tool_registry import invoke_agent_tool_sync

def select_search_tool(query: str, domain: str) -> str:
    lowered = query.casefold()
    if "histor" in lowered or "similar incident" in lowered:
        return "search_historical_incidents"
    return "search_company_policy" if domain == "ecommerce" else "search_technical_documentation"

def run(query: str, domain: str) -> dict:
    name = select_search_tool(query, domain)
    response = invoke_agent_tool_sync("rag", name, {"query": query}, timeout=settings.mcp_timeout_seconds)
    result = response.get("structuredContent", {})
    if not isinstance(result, dict): result = {}
    return {"documents": result.get("documents", []), "references": result.get("sources", []),
            "sources": result.get("sources", []), "evidence": result.get("documents", []),
            "mcp_server": "documents", "mcp_tools_used": [name]}

def retrieve(query: str, domain: str = "ecommerce") -> list[dict]:
    return run(query, domain).get("documents", [])
