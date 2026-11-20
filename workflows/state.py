"""Shared state contract for Operlynt LangGraph workflows."""
from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    user_query: str
    business_domain: str
    execution_plan: list[str]
    agent_results: dict[str, dict[str, Any]]
    retrieved_documents: list[dict[str, Any]]
    analytics_results: dict[str, Any]
    recommendations: list[dict[str, Any]]
    proposed_actions: list[dict[str, Any]]
    approval_status: str
    execution_results: dict[str, Any]
    errors: list[dict[str, Any]]
    final_response: str
    thread_id: str
    user_id: str
    conversation_history: list[dict[str, Any]]
    memory_context: list[str]
    # Phase 1/2 compatibility keys returned by the original workflows.
    query: str
    domain: str
    plan: list[str]
    findings: list[dict[str, Any]]
    answer: str
    sources: list[dict[str, Any]]
    needs_approval: bool
    action: dict[str, Any] | None
    action_result: dict[str, Any]
    agents: list[str]
    error: str
