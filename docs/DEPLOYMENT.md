# Deployment configuration

## Target environment

The included Docker Compose configuration targets a single Linux host or VM with Docker Engine and Compose v2. It is appropriate for a private portfolio/demo deployment and small controlled environments. For internet-facing production, put a maintained TLS reverse proxy/load balancer in front, enforce host firewall rules, use managed PostgreSQL/backups, and store secrets in the hosting platform’s secret manager. No deployment has been executed or verified as part of this repository work.

## Services and startup order

`docker-compose.yml` defines PostgreSQL 16, four MCP servers, FastAPI, and Streamlit. MCP servers use Streamable HTTP internally and are not published to host ports. Startup dependencies wait for PostgreSQL and protocol-level MCP health checks before the API starts. Streamlit waits for API readiness.

- Backend command: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- Frontend command: `streamlit run frontend/app.py --server.address=0.0.0.0 --server.port=8501`
- MCP command: `python -m mcp_servers.<server_module>` with `MCP_TRANSPORT=streamable-http`, `MCP_HOST=0.0.0.0`, and `MCP_PORT=8000`
- MCP client URLs are set by the API to each service’s internal `http://<service>:8000/mcp` endpoint.
- PostgreSQL is the Compose database. The API creates tables and seeds sample records on startup; for production use a migration system and controlled seed policy.

## Environment variables

Copy `.env.example` to `.env` and set at least:

| Variable | Required | Guidance |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | Yes | Generate a unique URL-safe random value. |
| `API_TOKEN` | Yes | Generate an independent random secret; retain compatibility token only where needed. |
| `JWT_SECRET` | Yes | Generate an independent random value (32+ characters). |
| `DEMO_MODE` | Recommended `true` for demo | Set `false` only with a supported live provider and its key. |
| `GROQ_API_KEY` / `OPENROUTER_API_KEY` | Only for live model use | Supply only via secret store/runtime environment. |
| `ADMIN_BOOTSTRAP_KEY` | Optional | Protect manager/admin account bootstrap. |
| `CORS_ORIGINS` | Yes for hosted UI | List exact browser UI origins; avoid broad wildcards. |
| `API_BIND` / `API_PORT` / `FRONTEND_PORT` | Optional | Defaults bind both exposed services to localhost. |
| `RAG_*`, `EMBEDDING_MODEL`, `MCP_TIMEOUT_SECONDS` | Optional | Tune retrieval/model and MCP timeout behavior. |

Compose constructs `DATABASE_URL` from the PostgreSQL service and `POSTGRES_PASSWORD`. Do not include a second conflicting database URL in the deployment environment unless you also update the Compose configuration intentionally. Compose secrets are supplied through environment interpolation; hosting environments should prefer native secret references or mounted secrets, with access limited to the API/MCP services that need each value.

For direct local SQLite mode, use `DATABASE_URL=sqlite:///./opspilot.db`. For a hosted PostgreSQL provider, configure a SQLAlchemy-compatible URL such as `postgresql+psycopg://<user>:<url-encoded-password>@<host>:5432/<database>` and provide network/TLS settings required by that provider.

## Persistent storage

Named Compose volumes store database records, vector indexes/metadata, uploaded files, LangGraph checkpoints, and cached Hugging Face model files. Mount durable disk for all volumes in a hosting environment. Define scheduled encrypted backups for PostgreSQL and document/vector/workflow data, retention, and tested restore procedures. Container replacement alone does not delete named volumes; `docker compose down -v` removes them.

## Secret handling

- Do not store real values in `.env.example`, Dockerfile, Compose defaults, GitHub Actions, or CI logs.
- The `.dockerignore` excludes `.env` and local model/database/vector/upload state from image builds.
- Locally, protect `.env` with filesystem access controls and keep it ignored by Git.
- On a host, provision variables from a secret manager at process startup; restrict secret readers and rotate credentials.
- For live mode, only the API needs an LLM provider key. Do not pass it into the UI or MCP services.
- This Compose file uses environment variables for ease of demonstration. Environment variables can be visible to privileged host users; use mounted secrets or platform secret references for higher assurance.

## Deploy with Docker Compose

On a prepared Linux host with Docker Compose v2:

```sh
cp .env.example .env
chmod 600 .env
# Edit .env and set POSTGRES_PASSWORD, API_TOKEN, and JWT_SECRET.
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

The default exposed host ports bind to `127.0.0.1`. This is suitable when a reverse proxy on the host connects through localhost. If binding to an external interface is required, set `API_BIND=0.0.0.0`, configure a firewall, and expose only the TLS proxy publicly. The API docs at `/docs` should be protected or disabled in a public production configuration.

Verify each container’s health with `docker compose ps`. Then check:

- `GET http://127.0.0.1:8000/health` for API liveness.
- `GET http://127.0.0.1:8000/health/ready` for API and PostgreSQL readiness.
- `http://127.0.0.1:8501` for Streamlit.
- MCP services’ Docker health status, which discovers tools through MCP protocol initialization.

This is a deployment recipe only. A successful local image build, if obtained, does not prove a production deployment.

## GitHub Actions

`.github/workflows/ci.yml` uses GitHub-hosted Ubuntu with Python 3.11. It installs pinned app dependencies and a pinned Ruff/pytest-timeout tool version, performs critical Ruff lint checks, compiles modules, checks application imports, caches the embedding model, and runs the automated tests in demo mode. No live API credentials are configured or required. CI execution status depends on a run in the GitHub repository and is not inferred from local files.
