"""Run the curated RAG retrieval set and print reproducible measured metrics."""
from __future__ import annotations

import json
import time
from pathlib import Path

from evaluation.evaluation_metrics import mean_reciprocal_rank, precision_at_k, recall_at_k
from rag.retriever import retrieve_documents

DATASET = Path(__file__).with_name("rag_cases.json")


def evaluate(top_k: int = 4) -> dict:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    rankings, relevant = [], []
    latencies = []
    for case in cases:
        started = time.perf_counter()
        results = retrieve_documents(case["query"], top_k=top_k)
        latencies.append((time.perf_counter() - started) * 1000)
        rankings.append([item["document"] for item in results])
        relevant.append(case["relevant_documents"])
    per_case = [{"id": case["id"], "precision_at_k": precision_at_k(ranking, target, top_k),
                 "recall_at_k": recall_at_k(ranking, target, top_k)}
                for case, ranking, target in zip(cases, rankings, relevant)]
    return {"dataset_cases": len(cases), "top_k": top_k, "precision_at_k": sum(x["precision_at_k"] for x in per_case) / len(per_case),
            "recall_at_k": sum(x["recall_at_k"] for x in per_case) / len(per_case),
            "mrr": mean_reciprocal_rank(rankings, relevant), "retrieval_latency_ms": latencies,
            "per_case": per_case}


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
