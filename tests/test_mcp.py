import asyncio
import json
import pytest
pytest.importorskip("mcp")
from mcp_clients.client_manager import call_tool
def test_database_tool_over_stdio():
    result=asyncio.run(call_tool("mcp_servers.database_server","get_return_statistics",{}))
    payload=json.loads(result["content"][0])
    assert payload["orders"]>=1000
