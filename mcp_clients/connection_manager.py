"""Reusable, timeout-aware connections to Operlynt MCP server processes."""
from __future__ import annotations
import asyncio
import atexit
import os
import sys
import threading
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import AsyncIterator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_MODULES = {
    "database": "mcp_servers.database_server",
    "ecommerce": "mcp_servers.ecommerce_server",
    "it_operations": "mcp_servers.it_operations_server",
    "documents": "mcp_servers.document_server",
}
ALIASES = {module: name for name, module in SERVER_MODULES.items()}
ALIASES.update({"it": "it_operations", "document": "documents"})

class MCPConnectionError(RuntimeError):
    """Safe error used for process startup, initialization, and protocol failures."""

def normalize_server(server: str) -> str:
    name = ALIASES.get(server, server)
    if name not in SERVER_MODULES: raise MCPConnectionError(f"Unknown MCP server: {server}")
    return name

def server_url(name: str) -> str | None:
    env_name = f"OPERLYNT_MCP_{name.upper()}_URL"
    legacy_name = f"OPSPILOT_MCP_{name.upper()}_URL"
    return os.getenv(env_name) or os.getenv(legacy_name) or None

@asynccontextmanager
async def connect_server(server: str, *, timeout: float = 20.0) -> AsyncIterator[ClientSession]:
    name = normalize_server(server)
    async with AsyncExitStack() as stack:
        try:
            url = server_url(name)
            if url:
                read, write, _ = await asyncio.wait_for(
                    stack.enter_async_context(streamablehttp_client(url, timeout=timeout)), timeout=timeout)
            else:
                params = StdioServerParameters(command=sys.executable,
                    args=["-m", SERVER_MODULES[name]], cwd=str(PROJECT_ROOT), env=os.environ.copy())
                read, write = await asyncio.wait_for(stack.enter_async_context(stdio_client(params)), timeout=timeout)
            session = await stack.enter_async_context(ClientSession(read, write, read_timeout_seconds=timedelta(seconds=timeout)))
            await asyncio.wait_for(session.initialize(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise MCPConnectionError(f"Timed out connecting to MCP server '{name}'.") from exc
        except MCPConnectionError: raise
        except Exception as exc:
            raise MCPConnectionError(f"Could not connect to MCP server '{name}' ({type(exc).__name__}).") from exc
        yield session

async def discover_tools(server: str, *, timeout: float = 20.0) -> list[dict]:
    name = normalize_server(server)
    try:
        async with connect_server(name, timeout=timeout) as session:
            result = await asyncio.wait_for(session.list_tools(), timeout=timeout)
            return [{"name": tool.name, "description": tool.description or "", "input_schema": tool.inputSchema}
                    for tool in result.tools]
    except asyncio.TimeoutError as exc: raise MCPConnectionError(f"Timed out listing tools from '{name}'.") from exc
    except MCPConnectionError: raise
    except Exception as exc: raise MCPConnectionError(f"Tool discovery failed for '{name}' ({type(exc).__name__}).") from exc

class PersistentMCPConnectionManager:
    """Owns long-lived MCP sessions on one event loop for synchronous agents."""
    def __init__(self):
        self._thread = threading.Thread(target=self._run_loop, name="operlynt-mcp-client", daemon=True)
        self._started = threading.Event(); self._loop = None; self._sessions = {}; self._locks = {}

    def _run_loop(self):
        self._loop = asyncio.new_event_loop(); asyncio.set_event_loop(self._loop)
        self._started.set(); self._loop.run_forever()

    def _ensure_started(self):
        if not self._thread.is_alive(): self._thread.start()
        self._started.wait()

    def submit(self, coro, timeout: float):
        self._ensure_started()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout + 5)

    async def _get_session(self, server: str, timeout: float):
        name = normalize_server(server)
        if name in self._sessions: return self._sessions[name][1]
        stack = AsyncExitStack(); await stack.__aenter__()
        try:
            url = server_url(name)
            if url:
                read, write, _ = await asyncio.wait_for(stack.enter_async_context(streamablehttp_client(url, timeout=timeout)), timeout)
            else:
                params = StdioServerParameters(command=sys.executable, args=["-m", SERVER_MODULES[name]],
                    cwd=str(PROJECT_ROOT), env=os.environ.copy())
                read, write = await asyncio.wait_for(stack.enter_async_context(stdio_client(params)), timeout)
            session = await stack.enter_async_context(ClientSession(read, write, read_timeout_seconds=timedelta(seconds=timeout)))
            await asyncio.wait_for(session.initialize(), timeout)
            self._sessions[name] = (stack, session); self._locks[name] = asyncio.Lock()
            return session
        except Exception:
            await stack.aclose()
            raise

    async def invoke(self, server: str, name: str, arguments: dict | None, timeout: float):
        resolved = normalize_server(server)
        session = await self._get_session(resolved, timeout)
        async with self._locks[resolved]:
            listed = await asyncio.wait_for(session.list_tools(), timeout)
            if name not in {tool.name for tool in listed.tools}:
                raise MCPConnectionError(f"Tool '{name}' is not registered on MCP server '{resolved}'.")
            return await asyncio.wait_for(session.call_tool(name, arguments or {}), timeout)

    async def _close(self):
        for stack, _ in list(self._sessions.values()):
            try: await stack.aclose()
            except Exception: pass
        self._sessions.clear()
        if self._loop: self._loop.stop()

    def close(self):
        if not self._thread.is_alive(): return
        try:
            future = asyncio.run_coroutine_threadsafe(self._close(), self._loop); future.result(5)
        except Exception: pass
        self._thread.join(timeout=5)

_persistent_manager = PersistentMCPConnectionManager()
atexit.register(_persistent_manager.close)

def invoke_persistent(server: str, name: str, arguments: dict | None = None, *, timeout: float = 20.0):
    return _persistent_manager.submit(_persistent_manager.invoke(server, name, arguments, timeout), timeout)
