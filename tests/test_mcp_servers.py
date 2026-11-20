import asyncio
from mcp_clients.client_manager import list_tools

EXPECTED = {
    "database": {"get_product_details", "get_return_statistics", "get_inventory_status", "get_support_ticket_statistics", "search_customer_complaints"},
    "ecommerce": {"get_order_details", "get_seller_performance", "get_product_return_rate", "create_ecommerce_escalation"},
    "it_operations": {"search_it_tickets", "get_incident_details", "create_it_ticket", "escalate_it_incident", "update_ticket_status"},
    "documents": {"search_company_policy", "search_technical_documentation", "search_historical_incidents"},
}

def test_all_four_servers_start_and_register_expected_tools():
    for server, names in EXPECTED.items():
        tools = asyncio.run(list_tools(server, timeout=30))
        assert names.issubset({tool["name"] for tool in tools})
        assert all(tool["input_schema"] for tool in tools if tool["name"] in names)

def test_server_metadata_uses_operlynt_product_identity():
    from mcp_servers.database_server import mcp as database
    from mcp_servers.ecommerce_server import mcp as ecommerce
    from mcp_servers.it_operations_server import mcp as it_operations
    from mcp_servers.document_server import mcp as documents
    assert [database.name,ecommerce.name,it_operations.name,documents.name] == [
        "operlynt-database","operlynt-ecommerce","operlynt-it-operations","operlynt-documents"]
