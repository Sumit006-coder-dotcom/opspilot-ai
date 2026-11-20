"""Classifies requests and creates a minimal, explicit agent execution plan."""
from __future__ import annotations

def plan(query: str, domain: str) -> list[str]:
    text = query.casefold()
    if domain == "ecommerce":
        domain_agent = "ecommerce"
    else:
        domain_agent = "it_operations"
    # The domain investigator always runs. Evidence gathering is conditional on
    # the question: broad operational questions benefit from all three sources.
    data_terms = ("metric", "rate", "trend", "count", "how many", "analy", "risk", "inventory", "ticket", "incident", "seller", "complaint", "compare", "pattern")
    research_terms = ("history", "historical", "recurring", "similar", "previous", "record", "ticket", "incident", "complaint", "seller", "investigat", "analy", "trend", "risk")
    rag_terms = ("policy", "document", "guide", "procedure", "troubleshoot", "recommend", "should", "how do", "return", "incident", "complaint", "investigat", "analy", "risk", "escalat")
    selected = [domain_agent]
    if any(term in text for term in data_terms): selected.append("data_analyst")
    if any(term in text for term in research_terms): selected.append("research")
    if any(term in text for term in rag_terms): selected.append("rag")
    if len(selected) == 1: selected.extend(["data_analyst", "research"])
    selected.append("decision")
    return selected

def route(query: str, domain: str) -> dict:
    agents = plan(query, domain)
    return {"business_domain": domain, "domain": domain,
            "execution_plan": agents, "plan": agents,
            "orchestration": {"intent": query, "selected_agents": agents,
                              "reason": "Selected from request intent and evidence needs."}}
