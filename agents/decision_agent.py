"""Decision synthesis separates database facts from plausible explanations."""
from __future__ import annotations
from config import settings

def decide(query: str, domain: str, findings: list[dict]) -> dict:
    by_agent = {item.get("agent"): item.get("result", {}) for item in findings if isinstance(item, dict)}
    specialist = by_agent.get("ecommerce" if domain == "ecommerce" else "it_operations", {})
    analytics = by_agent.get("data_analyst", {}).get("metrics", {})
    research = by_agent.get("research", {}).get("records", [])
    rag = by_agent.get("rag", {})
    facts = []
    if domain == "ecommerce":
        summary = specialist.get("return_summary", {}) or {"orders": analytics.get("orders", 0), "returns": analytics.get("returns", 0), "return_rate_pct": analytics.get("return_rate", 0)}
        if analytics or specialist.get("return_summary"): facts.append(f"Database contains {summary.get('orders', 0)} orders; {summary.get('returns', 0)} returned ({summary.get('return_rate_pct', 0)}%).")
        if specialist.get("complaint_categories"): facts.append(f"Complaint categories: {specialist['complaint_categories']}.")
        if specialist.get("low_inventory"): facts.append(f"{len(specialist['low_inventory'])} sampled products are below reorder point.")
        recommendations = ["Review leading complaint categories and verify affected product or seller records.", "Prioritize low stock where demand and replenishment lead time support action."]
        causes = ["Product quality issues may contribute to returns or complaints.", "Seller performance may contribute to customer complaints."]
    else:
        open_count = analytics.get("open_tickets", specialist.get("open_ticket_count"))
        critical_count = analytics.get("critical_tickets", specialist.get("critical_ticket_count", 0))
        if open_count is not None: facts.append(f"There are {open_count} unresolved tickets, including {critical_count} critical tickets.")
        if specialist.get("critical_incidents"): facts.append(f"Active critical incidents: {len(specialist['critical_incidents'])}.")
        if specialist.get("recurring_categories"): facts.append(f"Ticket category counts: {specialist['recurring_categories']}.")
        recommendations = ["Prioritize active critical incidents and validate service health.", "Compare recurring ticket categories with recent change history before remediation."]
        causes = ["A recent deployment or dependency failure may explain recurring service incidents."]
    if analytics and not analytics.get("error"):
        if domain == "ecommerce" and analytics.get("low_inventory_products") is not None:
            facts.append(f"SQL analytics counted {analytics['low_inventory_products']} low inventory products and {analytics.get('complaints', 0)} complaints.")
        elif domain == "it" and analytics.get("ticket_categories"):
            facts.append(f"SQL analytics confirm ticket category counts: {analytics['ticket_categories']}.")
    if not facts: facts.append("No structured business metrics were returned for this question.")
    refs = rag.get("references", [])
    if refs: recommendations.append("Use the cited policy or runbook evidence when choosing an operational response.")
    answer = " ".join(facts + ["Recommended next steps: " + " ".join(recommendations)])
    if settings.demo_mode: answer = "[SIMULATED DEMO ANALYSIS] " + answer
    return {"answer": answer,
            "confirmed_facts": facts, "possible_root_causes": causes, "hypotheses": causes,
            "recommendations": recommendations, "evidence_records": research, "sources": refs,
            "agent_contributions": sorted(by_agent), "analytics": analytics}
