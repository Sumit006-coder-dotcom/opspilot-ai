"""IT operations specialist using discovered IT Operations MCP tools."""
from __future__ import annotations
import re
from config import settings
from mcp_clients.tool_registry import invoke_agent_tool_sync

def investigate(query: str) -> dict:
    response = invoke_agent_tool_sync("it_operations", "search_it_tickets", {"query": query[:500], "limit": 25}, timeout=settings.mcp_timeout_seconds)
    result = response.get("structuredContent", {})
    if not isinstance(result, dict): result = {}
    tickets = result.get("tickets", [])
    incident_match = re.search(r"\bincident(?:\s+id)?\s*#?\s*(\d+)\b", query, re.I)
    incidents = []
    tools = ["search_it_tickets"]
    if incident_match:
        detail = invoke_agent_tool_sync("it_operations", "get_incident_details", {"incident_id": int(incident_match.group(1))}, timeout=settings.mcp_timeout_seconds)
        incidents.append(detail.get("structuredContent", {})); tools.append("get_incident_details")
    counts = {}
    for row in tickets: counts[row.get("category", "other")] = counts.get(row.get("category", "other"), 0) + 1
    critical = [row for row in tickets if row.get("severity") == "critical" and row.get("status") != "resolved"]
    return {"domain": "it", "query_focus": query, "mcp_server": "it_operations", "mcp_tools_used": tools,
            "open_ticket_count": len([row for row in tickets if row.get("status") != "resolved"]),
            "critical_ticket_count": len(critical),
            "recurring_categories": [{"category": key, "count": count} for key, count in sorted(counts.items(), key=lambda item: -item[1])],
            "sample_open_tickets": tickets, "incident_evidence": incidents,
            "troubleshooting": ["Confirm affected service and scope", "Check recent changes and service health", "Escalate active critical incidents"]}
