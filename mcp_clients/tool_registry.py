"""Agent allow-lists layered over tools discovered from live MCP servers."""
from __future__ import annotations
from mcp_clients.client_manager import MCPToolError, call_tool, call_tool_sync
from mcp_clients.connection_manager import discover_tools

AGENT_SERVERS = {
    "data_analyst": "database",
    "ecommerce": "ecommerce",
    "it_operations": "it_operations",
    "rag": "documents",
    "execution": "it_operations",
}
AGENT_ALLOWED_TOOLS = {
    "data_analyst": {"get_product_details", "get_return_statistics", "get_inventory_status", "get_support_ticket_statistics", "search_customer_complaints"},
    "ecommerce": {"get_order_details", "get_seller_performance", "get_product_return_rate"},
    "it_operations": {"search_it_tickets", "get_incident_details"},
    "rag": {"search_company_policy", "search_technical_documentation", "search_historical_incidents"},
    "execution": {"create_ecommerce_escalation", "create_it_ticket", "escalate_it_incident", "update_ticket_status"},
}
WRITE_TOOLS = {"create_ecommerce_escalation", "create_it_ticket", "escalate_it_incident", "update_ticket_status"}

async def discover_agent_tools(agent: str, *, timeout: float = 20.0) -> list[dict]:
    if agent not in AGENT_SERVERS: raise MCPToolError(f"Unknown agent MCP role: {agent}")
    server_tools = await discover_tools(AGENT_SERVERS[agent], timeout=timeout)
    allowed = AGENT_ALLOWED_TOOLS[agent]
    return [tool for tool in server_tools if tool["name"] in allowed]

async def invoke_agent_tool(agent: str, name: str, arguments: dict, *, timeout: float = 20.0,
                           authorized_execution: bool = False) -> dict:
    if agent not in AGENT_SERVERS or name not in AGENT_ALLOWED_TOOLS.get(agent, set()):
        raise MCPToolError(f"Agent '{agent}' is not permitted to invoke '{name}'.")
    if name in WRITE_TOOLS and not authorized_execution:
        raise MCPToolError(f"Write tool '{name}' requires an approved Execution Agent context.")
    server = AGENT_SERVERS[agent]
    if agent == "execution" and name == "create_ecommerce_escalation": server = "ecommerce"
    # call_tool performs a fresh protocol-level list_tools before dispatch, so
    # agent permission checks remain local and server registrations stay dynamic.
    return await call_tool(server, name, arguments, timeout=timeout)

def invoke_agent_tool_sync(agent: str, name: str, arguments: dict, *, timeout: float = 20.0,
                           authorized_execution: bool = False) -> dict:
    if agent not in AGENT_SERVERS or name not in AGENT_ALLOWED_TOOLS.get(agent, set()):
        raise MCPToolError(f"Agent '{agent}' is not permitted to invoke '{name}'.")
    if name in WRITE_TOOLS and not authorized_execution:
        raise MCPToolError(f"Write tool '{name}' requires an approved Execution Agent context.")
    server = AGENT_SERVERS[agent]
    if agent == "execution" and name == "create_ecommerce_escalation": server = "ecommerce"
    return call_tool_sync(server, name, arguments, timeout=timeout)

