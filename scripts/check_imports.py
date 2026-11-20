"""Import-check the application modules without starting external services."""
from __future__ import annotations

import importlib


MODULES = (
    "api.main",
    "agents.orchestrator",
    "agents.data_analyst_agent",
    "agents.rag_agent",
    "database.models",
    "evaluation.evaluate_agents",
    "evaluation.evaluate_rag",
    "frontend.api_client",
    "llm.provider",
    "mcp_clients.client_manager",
    "mcp_servers.database_server",
    "mcp_servers.document_server",
    "mcp_servers.ecommerce_server",
    "mcp_servers.it_operations_server",
    "rag.chain",
    "workflows.engine",
)


def main() -> None:
    for module in MODULES:
        importlib.import_module(module)
        print(f"import ok: {module}")


if __name__ == "__main__":
    main()
