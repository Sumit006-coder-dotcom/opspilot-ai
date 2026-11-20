"""Evaluate deterministic routing and RAG-tool decisions on curated cases."""
from __future__ import annotations

import json
from pathlib import Path

from agents.orchestrator import plan
from agents.rag_agent import select_search_tool
from evaluation.evaluation_metrics import accuracy


def evaluate() -> dict:
    cases = json.loads(Path(__file__).with_name("agent_cases.json").read_text(encoding="utf-8"))
    actual_plans = [plan(case["query"], case["domain"]) for case in cases]
    expected_plans = [case["expected_agents"] for case in cases]
    actual_tools = [select_search_tool(case["query"], case["domain"]) for case in cases]
    expected_tools = [case["expected_rag_tool"] for case in cases]
    return {
        "dataset_cases": len(cases),
        "agent_selection_exact_match": accuracy(actual_plans, expected_plans),
        "rag_tool_selection_accuracy": accuracy(actual_tools, expected_tools),
        "cases": [{"id": case["id"], "expected_agents": expected_plans[i], "actual_agents": actual_plans[i],
                   "expected_rag_tool": expected_tools[i], "actual_rag_tool": actual_tools[i]}
                  for i, case in enumerate(cases)],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
