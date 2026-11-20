"""Keep graph tests deterministic; document MCP has its own integration suite."""
import pytest


@pytest.fixture(autouse=True)
def deterministic_graph_rag(monkeypatch):
    from workflows import engine

    monkeypatch.setattr(
        engine.rag_agent,
        "run",
        lambda *_args, **_kwargs: {
            "documents": [],
            "references": [],
            "evidence": [],
            "sources": [],
        },
    )
