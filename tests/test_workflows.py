from workflows.ecommerce_workflow import run as run_ecommerce
from workflows.it_workflow import run as run_it
from workflows.engine import get_workflow_state, resume_approval
from database.connection import SessionLocal
from database.models import Approval

def test_both_domains_collaborate_in_demo_mode():
    ecommerce = run_ecommerce("Analyze return trends and policy recommendations")
    it = run_it("Analyze recurring IT incidents and troubleshooting recommendations")
    assert ecommerce["business_domain"] == "ecommerce"
    assert it["business_domain"] == "it"
    assert {"ecommerce", "data_analyst", "research", "rag", "decision"}.issubset(ecommerce["agents"])
    assert {"it_operations", "data_analyst", "research", "rag", "decision"}.issubset(it["agents"])
    assert ecommerce["analytics_results"]["orders"] >= 1000
    assert it["analytics_results"]["open_tickets"] > 0
    assert "sources" in ecommerce["agent_results"]["rag"]

def test_explicit_action_pauses_until_approval_then_executes():
    result = run_it("Escalate incident after approval", {"type": "escalate_it_incident", "incident_id": 1, "reason": "Test approved escalation"})
    assert result["approval_status"] == "pending"
    assert result["approval_interrupt"]["type"] == "approval_required"
    approval_id=result["action_result"]["approval_id"]
    # The API persists the approved decision before resuming the graph; mirror
    # that durable gate here so the real MCP write authorizer sees approval.
    db=SessionLocal()
    try:
        approval=db.get(Approval,approval_id)
        approval.status="approved"
        db.commit()
    finally: db.close()
    resumed = resume_approval(result["thread_id"], True, approval_id)
    assert resumed["approval_status"] == "approved"
    assert resumed["execution_results"]["status"] == "executed"

def test_agent_error_is_retried_and_recorded(monkeypatch):
    from workflows import engine
    calls = {"count": 0}
    def fail_research(*args, **kwargs):
        calls["count"] += 1
        raise RuntimeError("simulated research failure")
    monkeypatch.setattr(engine.research_agent, "research", fail_research)
    result = run_ecommerce("Analyze historical complaint records")
    assert calls["count"] == 2
    assert any(error["agent"] == "research" for error in result["errors"])
    assert result["final_response"]

