from workflows.ecommerce_workflow import run as ecommerce
from workflows.it_workflow import run as it
def test_workflows():
    a=ecommerce("Analyze returns")
    b=it("Analyze critical incidents")
    assert "data_analyst" in a["agents"] and "research" in a["agents"]
    assert b["domain"]=="it" and "it_operations" in b["agents"]
def test_action_requires_approval():
    r=it("Escalate a critical incident",{"type":"escalate","incident_id":1})
    assert r["action_result"]["status"]=="pending"
