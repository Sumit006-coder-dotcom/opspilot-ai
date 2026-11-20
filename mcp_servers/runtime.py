"""Lifecycle helpers shared by real MCP FastMCP servers."""
from __future__ import annotations
import logging
import os
import sys
from mcp.server.fastmcp import FastMCP

def create_server(name: str) -> FastMCP:
    logging.basicConfig(level=os.getenv("MCP_LOG_LEVEL", "INFO"), stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    return FastMCP(name, instructions=f"Operlynt {name} MCP server. Use only registered tools; writes enforce approval checks.",
                   host=os.getenv("MCP_HOST", "127.0.0.1"), port=int(os.getenv("MCP_PORT", "8000")),
                   log_level=os.getenv("MCP_LOG_LEVEL", "INFO"))

def serve(server: FastMCP) -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport not in {"stdio", "streamable-http", "sse"}:
        raise ValueError("MCP_TRANSPORT must be stdio, streamable-http, or sse")
    logging.getLogger("operlynt.mcp").info("Starting %s over %s", server.name, transport)
    server.run(transport=transport)
