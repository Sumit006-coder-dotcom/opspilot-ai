from agents.data_analyst_agent import analyze
from agents.ecommerce_agent import investigate as investigate_ecommerce
from agents.it_operations_agent import investigate as investigate_it
from agents.rag_agent import run as retrieve_documents

def test_agents_discover_and_invoke_their_mcp_servers():
    metrics = analyze("ecommerce", "return rate")
    ecommerce = investigate_ecommerce("Inspect order 1")
    it = investigate_it("network ticket")
    # Keep the MCP integration check independent from downloading/loading the
    # optional sentence-transformer model. The short query still crosses the
    # real stdio MCP client/server boundary and exercises server validation.
    docs = retrieve_documents("x", "ecommerce")
    assert metrics["source"] == "Database MCP server" and metrics["orders"] >= 1000
    assert ecommerce["mcp_tools_used"] == ["get_order_details"]
    assert ecommerce["record_evidence"]["get_order_details"]["ok"] is True
    assert it["mcp_tools_used"] == ["search_it_tickets"]
    assert docs["mcp_tools_used"] == ["search_company_policy"]
    assert docs["sources"] == []
