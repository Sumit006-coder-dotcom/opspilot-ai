import pytest

from evaluation.evaluation_metrics import (
    accuracy, action_execution_success_rate, agent_selection_accuracy, answer_groundedness, context_relevance,
    mean_reciprocal_rank, precision_at_k, recall_at_k,
    sql_analytical_correctness, task_completion_rate, token_overlap_faithfulness, tool_selection_accuracy,
    unsupported_claim_rate, workflow_success_rate,
)
from evaluation.evaluate_agents import evaluate as evaluate_agents


def test_agent_metrics_are_deterministic_and_do_not_truncate_mismatched_cases():
    assert accuracy(["analyst", "rag"], ["analyst", "research"]) == 0.5
    with pytest.raises(ValueError):
        accuracy(["analyst"], ["analyst", "rag"])
    assert task_completion_rate([True, False, True]) == pytest.approx(2 / 3)
    assert workflow_success_rate([True, True]) == 1.0
    assert action_execution_success_rate(["executed", "rejected", "error"]) == pytest.approx(1 / 3)
    assert agent_selection_accuracy(["rag"], ["rag"]) == 1.0
    assert tool_selection_accuracy(["search"], ["search"]) == 1.0
    assert sql_analytical_correctness([42], [42]) == 1.0


def test_rag_ranking_and_grounding_metrics():
    ranked = ["noise", "policy", "faq"]
    relevant = ["policy", "faq"]
    assert precision_at_k(ranked, relevant, 2) == 0.5
    assert recall_at_k(ranked, relevant, 2) == 0.5
    assert mean_reciprocal_rank([ranked, ["faq"]], [relevant, relevant]) == 0.75
    assert context_relevance(ranked, relevant) == pytest.approx(2 / 3)
    assert token_overlap_faithfulness("return policy applies", ["return policy applies here"]) == 1.0
    assert answer_groundedness("return policy applies", ["return policy applies here"]) == 1.0
    assert unsupported_claim_rate(["supported", "invented"], ["supported"]) == 0.5


def test_metric_boundaries():
    assert precision_at_k([], [], 4) == 0.0
    assert recall_at_k([], [], 4) == 0.0
    assert mean_reciprocal_rank([], []) == 0.0
    with pytest.raises(ValueError):
        precision_at_k([], [], 0)


def test_curated_agent_evaluation_is_repeatable():
    first = evaluate_agents()
    assert first == evaluate_agents()
    assert first["dataset_cases"] == 3
    assert first["agent_selection_exact_match"] == 1.0
    assert first["rag_tool_selection_accuracy"] == 1.0
