import asyncio
from mcp_clients.client_manager import call_tool, list_tools

def test_mcp_client_discovers_tools_and_decodes_structured_result():
    tools = asyncio.run(list_tools("database", timeout=30))
    assert "get_return_statistics" in {tool["name"] for tool in tools}
    result = asyncio.run(call_tool("database", "get_return_statistics", {}, timeout=30))
    assert result["isError"] is False
    assert result["structuredContent"]["ok"] is True
    assert result["structuredContent"]["orders"] >= 1000

def test_unknown_tool_and_server_fail_safely():
    from mcp_clients.client_manager import MCPToolError
    from mcp_clients.connection_manager import MCPConnectionError
    try: asyncio.run(call_tool("database", "not_registered", {}))
    except MCPToolError as exc: assert "not registered" in str(exc)
    else: raise AssertionError("unknown tool should be rejected")
    try: asyncio.run(list_tools("not-a-server"))
    except MCPConnectionError as exc: assert "Unknown MCP server" in str(exc)
    else: raise AssertionError("unknown server should be rejected")

def test_operlynt_mcp_endpoint_names_prefer_new_env_with_legacy_fallback(monkeypatch):
    from mcp_clients.connection_manager import server_url
    monkeypatch.delenv("OPERLYNT_MCP_DATABASE_URL",raising=False)
    monkeypatch.setenv("OPSPILOT_MCP_DATABASE_URL","http://legacy.example/mcp")
    assert server_url("database")=="http://legacy.example/mcp"
    monkeypatch.setenv("OPERLYNT_MCP_DATABASE_URL","http://operlynt.example/mcp")
    assert server_url("database")=="http://operlynt.example/mcp"
