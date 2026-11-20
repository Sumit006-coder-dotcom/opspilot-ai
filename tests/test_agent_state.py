from workflows.state import WorkflowState
from workflows.engine import get_workflow_state

def test_state_contract_contains_phase3_fields():
    required = {"user_query", "business_domain", "execution_plan", "agent_results", "retrieved_documents", "analytics_results", "recommendations", "proposed_actions", "approval_status", "execution_results", "errors", "final_response"}
    assert required.issubset(WorkflowState.__annotations__)

def test_unknown_thread_has_empty_state():
    result = get_workflow_state("thread-that-does-not-exist", "test-user")
    assert result["state"] == {}

def test_conversation_continuation_preserves_thread_memory():
    from workflows.it_workflow import run
    run("Count open tickets", thread_id="memory-test-thread", user_id="memory-test-user")
    run("Now summarize the critical incidents", thread_id="memory-test-thread", user_id="memory-test-user")
    state = get_workflow_state("memory-test-thread", "memory-test-user")["state"]
    assert len(state["conversation_history"]) == 2
    assert state["memory_context"] == ["Count open tickets"]
