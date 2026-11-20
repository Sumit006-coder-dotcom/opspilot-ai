"""Deterministic, dependency-free metrics for agent and RAG evaluations."""
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def accuracy(actual: Sequence[object], expected: Sequence[object]) -> float:
    if len(actual) != len(expected):
        raise ValueError("actual and expected must have the same number of cases")
    return _ratio(sum(a == e for a, e in zip(actual, expected)), len(expected))


def exact_tool_accuracy(actual: list[str], expected: list[str]) -> float:
    return accuracy(actual, expected)


def agent_selection_accuracy(actual: Sequence[str], expected: Sequence[str]) -> float:
    return accuracy(actual, expected)


def tool_selection_accuracy(actual: Sequence[str], expected: Sequence[str]) -> float:
    return accuracy(actual, expected)


def sql_analytical_correctness(actual: Sequence[object], expected: Sequence[object]) -> float:
    """Exact result correctness for deterministic SQL-answer fixtures."""
    return accuracy(actual, expected)


def task_completion_rate(completed: Sequence[bool]) -> float:
    return _ratio(sum(bool(x) for x in completed), len(completed))


def workflow_success_rate(successes: Sequence[bool]) -> float:
    return task_completion_rate(successes)


def action_execution_success_rate(statuses: Sequence[str]) -> float:
    return _ratio(sum(status == "executed" for status in statuses), len(statuses))


def precision_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    relevant_set = set(relevant)
    top = list(retrieved[:k])
    return _ratio(sum(item in relevant_set for item in top), k)


def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    relevant_set = set(relevant)
    return _ratio(len(set(retrieved[:k]) & relevant_set), len(relevant_set))


def retrieval_recall(retrieved: list[str], relevant: list[str]) -> float:
    return recall_at_k(retrieved, relevant, max(1, len(retrieved)))


def mean_reciprocal_rank(rankings: Sequence[Sequence[str]], relevant_by_query: Sequence[Iterable[str]]) -> float:
    if len(rankings) != len(relevant_by_query):
        raise ValueError("rankings and relevant_by_query must have the same number of queries")
    reciprocal_ranks = []
    for ranking, relevant in zip(rankings, relevant_by_query):
        relevant_set = set(relevant)
        rank = next((i for i, item in enumerate(ranking, 1) if item in relevant_set), None)
        reciprocal_ranks.append(1 / rank if rank else 0.0)
    return _ratio(sum(reciprocal_ranks), len(reciprocal_ranks))


def context_relevance(retrieved: Sequence[str], relevant: Iterable[str], k: int | None = None) -> float:
    """Binary relevance precision over returned contexts (duplicates count once)."""
    relevant_set = set(relevant)
    contexts = list(dict.fromkeys(retrieved[:k] if k is not None else retrieved))
    return _ratio(sum(item in relevant_set for item in contexts), len(contexts))


def token_overlap_faithfulness(answer: str, contexts: Sequence[str]) -> float:
    """Transparent lexical proxy; not a semantic or human faithfulness judgment."""
    answer_tokens = set(re.findall(r"\b[\w'-]+\b", answer.lower()))
    context_tokens = set(re.findall(r"\b[\w'-]+\b", " ".join(contexts).lower()))
    return _ratio(len(answer_tokens & context_tokens), len(answer_tokens))


def answer_groundedness(answer: str, contexts: Sequence[str]) -> float:
    return token_overlap_faithfulness(answer, contexts)


def unsupported_claim_rate(claims: Sequence[str], supported_claims: Iterable[str]) -> float:
    supported = set(supported_claims)
    return _ratio(sum(claim not in supported for claim in claims), len(claims))
