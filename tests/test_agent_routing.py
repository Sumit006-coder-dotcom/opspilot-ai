from agents.orchestrator import plan

def test_routing_selects_only_relevant_evidence_agents():
    plan_out = plan("show me inventory metrics and trends", "ecommerce")
    assert plan_out == ["ecommerce", "data_analyst", "research", "decision"]
    policy = plan("What does the return policy say?", "ecommerce")
    assert "rag" in policy and "data_analyst" not in policy

def test_domain_agent_route():
    assert plan("prioritize critical incidents", "it")[0] == "it_operations"
