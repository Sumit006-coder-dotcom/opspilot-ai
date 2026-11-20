# OpsPilot AI Quality and Performance Report

**Run date:** 2026-11-18  
**Local environment:** Windows, Python 3.13.7, pytest 8.4.2, SQLite, local stdio MCP

## Test results

The latest full command, `python -m pytest -q`, completed:

- **60 tests collected**
- **59 passed**
- **1 skipped**
- **0 failed**
- **120.51 seconds**

The skipped case is the real Hugging Face model download/inference integration test. It requires `RUN_HF_MODEL_TESTS=1`; this avoids a network-dependent model download during local runs. The embedding adapter and deterministic embedding behavior were tested locally. CI sets the flag and caches the Hugging Face model, so the live model integration runs there when GitHub Actions is executed. That CI execution has not yet been observed.

After this suite completed, a user startup trace exposed a compatibility issue between installed MCP 1.9.2 and Pydantic 2.14.3. `requirements.txt` now pins MCP 1.29.1, whose metadata parser does not use the removed Pydantic helper. The 60-test result above used the previously installed MCP 1.9.2 and does not verify the newly pinned MCP version. Reinstall and rerun tests before treating the updated dependency set as fully validated.

The first full run after making workflows deterministic found two issues: the adapter fixture returned a list without `.tolist()`, and the graph approval test resumed without persisting approval. Both were fixed and retested. The final full suite above passed.

Coverage includes database and MCP queries/tool validation, provider configuration, embedding adapter, RAG ingestion/retrieval/citations, LangGraph state/workflows, agent routing, MCP client/server integration, API/auth/roles, approval operations, Streamlit UI rendering/client behavior, and deterministic metric/observability helpers. The graph tests stub only the graph RAG node; actual document MCP protocol and FAISS retrieval are exercised in their own tests.

## Agent evaluation results

`python -m evaluation.evaluate_agents` executed on `evaluation/agent_cases.json`:

| Metric | Result | Scope |
| --- | ---: | --- |
| Agent selection exact match | 1.00 (3/3) | Deterministic keyword planner |
| RAG tool selection accuracy | 1.00 (3/3) | Deterministic tool selector |

These scores apply only to three curated deterministic cases. They do not represent a production quality estimate or measure live-model answer quality.

## RAG evaluation status

`evaluation/rag_cases.json` contains manually curated retrieval cases. `evaluation/evaluate_rag.py` computes Precision@K, Recall@K, MRR, and per-case retrieval results using the live configured retriever. It was **not run** in this validation; no retrieval score is reported. Context relevance and lexical token-overlap groundedness helpers are available. The lexical score is not semantic or human faithfulness judgment. Unsupported-claim, SQL correctness, task completion, workflow success, and action execution metrics are implemented as deterministic helpers but do not yet have measured labeled end-to-end results.

## Performance observations

The local measurements in `evaluation/performance_results.json` are small sequential smoke samples, not load tests:

| Scenario | Sample | Median | P95 / max | Notes |
| --- | ---: | ---: | ---: | --- |
| FastAPI `GET /health` | 20 requests | 5.03 ms client elapsed | P95 5.877 ms; max 8.186 ms | All HTTP 200. Server middleware values were approximately 1.0–2.8 ms. |
| MCP `database.get_return_statistics` | 5 calls | 23.55 ms | max 5,177.713 ms | First call includes startup and tool discovery; warm calls were 20.452–24.054 ms. |
| RAG retrieval | Not measured | — | — | Live retrieval evaluation not run. |
| Full agent workflow | Not load-measured | — | — | Workflow node duration events are emitted; no representative benchmark was saved. |

Do not treat these results as capacity or SLA commitments.

## Deployment and validation status

- Docker Compose parsed successfully with temporary process-only dummy values for required secret interpolation. No secret values were written into project files or images.
- Docker image build was attempted, but the Docker Engine was unavailable at `dockerDesktopLinuxEngine`; image build and container health checks could not be performed.
- FastAPI liveness and SQLite readiness endpoints passed in API tests. PostgreSQL health was not verified in a running container.
- Local stdio MCP integration and database tool checks passed in the full test run. Compose Streamable HTTP MCP health was not run.
- Streamlit started locally and `/_stcore/health` returned HTTP 200. The UI’s automated render/client tests passed.
- Python compile and import checks passed.
- Ruff is configured in CI but was not installed locally, so the Ruff command was not executed here. GitHub Actions has not been run.
- No external hosting deployment was performed.

## Structured observability

JSON events record API request completion/errors, workflow completion/errors, agent starts/completions, MCP calls, LLM requests/errors, and approval operations. Request/workflow IDs are carried where available. Events include durations, provider, status, and safe error type; prompts, credentials, personal data, and MCP arguments are omitted. API responses include `X-Request-ID` and `X-Process-Time-Ms`. Provider token usage is logged when returned; no live provider token metadata was available in this demo-mode run.

## Known limitations

- The Hugging Face model integration test and RAG evaluation require model files/network and were skipped/not run locally; CI is configured to attempt the model test.
- Rate limits, live provider outages, remote MCP disconnection/timeouts, database outage, malformed document variants, and approval timeout do not all have complete deterministic fault-injection cases.
- The RAG/agent evaluation sets are small. SQL analytical correctness, groundedness, and unsupported claims need a larger labeled answer corpus and review.
- Performance validation does not cover PostgreSQL, live LLM calls, RAG, workflow throughput, concurrency, or resource usage.
- The app has process-local password throttling and no external SSO, tenant isolation, centralized telemetry backend, or migration framework.
- Existing FastAPI, SQLAlchemy, and LangGraph dependency deprecation warnings remain.

## Reproduction

```cmd
python -m pytest -q
python -m evaluation.evaluate_agents
python -m evaluation.evaluate_rag
```

To include the model download/inference integration test, set `RUN_HF_MODEL_TESTS=1` before running pytest.
