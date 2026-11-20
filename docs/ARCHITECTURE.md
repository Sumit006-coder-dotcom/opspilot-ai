# Architecture

## Runtime components

| Component | Runtime responsibility | State |
| --- | --- | --- |
| FastAPI (`api.main:app`) | Authenticated API, upload/ask endpoints, workflow entry points, readiness probes | PostgreSQL, vector directory, upload and workflow volumes |
| Streamlit (`frontend/app.py`) | Operations dashboard and authenticated API client | Browser/session state |
| PostgreSQL | Users, seeded operations records, approvals, agent/audit rows | `pgdata` Compose volume |
| Database MCP | Read-only operational analytics/search tools | PostgreSQL |
| E-commerce MCP | Order/product/seller lookup and approval-gated escalation | PostgreSQL |
| IT operations MCP | Ticket/incident lookup and approval-gated changes | PostgreSQL |
| Documents MCP | Policy, runbook, and historical document retrieval | Shared vector volume and model cache |

Compose uses four distinct Streamable HTTP MCP services on the private network. The `mcp_clients.connection_manager` maps them using `OPERLYNT_MCP_DATABASE_URL`, `OPERLYNT_MCP_ECOMMERCE_URL`, `OPERLYNT_MCP_IT_OPERATIONS_URL`, and `OPERLYNT_MCP_DOCUMENTS_URL`. In direct local development, unset these values and the client starts each server as a stdio subprocess.

## Request path

The API assigns a request identifier and records structured completion or error events. Investigation requests enter the domain LangGraph, which selects an agent plan, invokes only registry-approved MCP tools, stores evidence and failures in workflow state, and builds a response. Tool write operations require approval. Approval decisions are stored conditionally so an approval can resolve only once, then execution and audit details are recorded.

Document upload parses PDF or TXT, splits content, embeds chunks, stores vectors in a domain FAISS collection, and stores source metadata. Retrieval applies the domain collection and similarity threshold, then returns citation metadata. In demo mode, answer text is assembled from retrieved snippets without calling a hosted model.

## Persistence

SQLite is the local development default. `database/connection.py` reads `DATABASE_URL`. The Docker API and all operational MCP servers use the Compose PostgreSQL service. LangGraph checkpoints use `WORKFLOW_CHECKPOINT_PATH`; FAISS and citation metadata use `VECTOR_DIR`; uploads use `UPLOAD_DIR`.

| Compose volume | Container path | Data |
| --- | --- | --- |
| `pgdata` | PostgreSQL data directory | Relational database |
| `vectordata` | `/app/data/vector_store` | FAISS indexes and metadata |
| `upload_data` | `/app/data/uploads` | Uploaded source files |
| `workflow_data` | `/app/data/workflows` | SQLite workflow checkpoints |
| `modelcache` | `/home/opspilot/.cache/huggingface` | Downloaded embedding model files |

The document MCP and API share the vector and model-cache volumes. Back up persistent data and test restoration before upgrading.

## Test and evaluation layout

- `tests/`: unit, API, UI, database/MCP integration, workflow, auth, and approval checks.
- `evaluation/agent_cases.json`: manually curated deterministic router/tool cases.
- `evaluation/rag_cases.json`: manually curated query/document relevance cases.
- `evaluation/evaluation_metrics.py`: generic deterministic accuracy, task/action/workflow, ranking, context-relevance, and lexical groundedness helpers.
- `evaluation/REPORT.md`: measured test/evaluation/performance state with unverified items called out.

## Trust boundaries

The UI sends requests to the API. The API and MCP containers communicate on the private Compose network. MCP calls use per-agent allow-lists; server tools validate argument domains and approval state. The API protects routes with JWT and role checks. Compose publishes only API/UI ports, bound to localhost by default. A public deployment needs TLS termination, firewall rules, strong secret management, and external access controls.
