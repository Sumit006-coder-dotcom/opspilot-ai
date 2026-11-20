"""Operlynt MCP SDK client operations with structured result normalization."""
from __future__ import annotations
import asyncio
import json
from typing import Any
from mcp_clients.connection_manager import MCPConnectionError, connect_server, discover_tools, invoke_persistent, normalize_server
from observability import timed_event

class MCPToolError(RuntimeError):
    """Safe MCP tool invocation error."""

def _normalize_result(result: Any) -> dict:
    if result.isError:
        text = "MCP tool returned an error."
        for block in result.content or []:
            if getattr(block, "text", None): text = block.text[:500]; break
        raise MCPToolError(text)
    structured = getattr(result, "structuredContent", None)
    if structured is not None: output = structured
    else:
        texts = [block.text for block in (result.content or []) if getattr(block, "text", None)]
        if len(texts) == 1:
            try: output = json.loads(texts[0])
            except json.JSONDecodeError: output = texts[0]
        else: output = texts
    return {"structuredContent": output,
            "content": [block.text for block in (result.content or []) if getattr(block, "text", None)],
            "isError": False}

async def list_tools(server: str, *, timeout: float = 20.0) -> list[dict]:
    return await discover_tools(server, timeout=timeout)

async def call_tool(server: str, name: str, arguments: dict | None = None, *, timeout: float = 20.0) -> dict:
    resolved = normalize_server(server)
    with timed_event("mcp.tool", server=resolved, tool=name, transport="async"):
        try:
            async with connect_server(resolved, timeout=timeout) as session:
                available = await asyncio.wait_for(session.list_tools(), timeout=timeout)
                if name not in {tool.name for tool in available.tools}: missing = True
                else:
                    missing = False
                    result = await asyncio.wait_for(session.call_tool(name, arguments or {}), timeout=timeout)
                    output = _normalize_result(result)
            if missing: raise MCPToolError(f"Tool '{name}' is not registered on MCP server '{resolved}'.")
            return output
        except asyncio.TimeoutError as exc: raise MCPToolError(f"MCP tool '{name}' timed out.") from exc
        except (MCPConnectionError, MCPToolError): raise
        except Exception as exc: raise MCPToolError(f"MCP tool '{name}' failed ({type(exc).__name__}).") from exc

def call_tool_sync(server: str, name: str, arguments: dict | None = None, *, timeout: float = 20.0) -> dict:
    """Use a pooled live MCP session for synchronous LangGraph agent nodes."""
    resolved = normalize_server(server)
    with timed_event("mcp.tool", server=resolved, tool=name, transport="persistent"):
        try: return _normalize_result(invoke_persistent(resolved, name, arguments, timeout=timeout))
        except MCPConnectionError as exc: raise MCPToolError(str(exc)) from exc
        except Exception as exc: raise MCPToolError(f"MCP tool '{name}' failed ({type(exc).__name__}).") from exc

