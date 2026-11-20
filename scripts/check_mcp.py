"""Return success when a configured MCP endpoint completes protocol discovery."""
from __future__ import annotations

import argparse
import asyncio
import os

from mcp_clients.connection_manager import normalize_server
from mcp_clients.client_manager import list_tools


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("server", nargs="?", default="database")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    server = normalize_server(args.server)
    variable = f"OPERLYNT_MCP_{server.upper()}_URL"
    if not os.getenv(variable):
        parser.error(f"{variable} must point to the MCP Streamable HTTP endpoint")
    tools = asyncio.run(list_tools(server, timeout=args.timeout))
    if not tools:
        raise SystemExit(f"MCP server '{server}' returned no tools")
    print(f"{server}: {len(tools)} tools discovered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
