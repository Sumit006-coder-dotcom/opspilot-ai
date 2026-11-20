import asyncio
from mcp_clients.client_manager import call_tool
from database.connection import SessionLocal
from database.models import Ticket

def test_mcp_read_tools_query_live_database():
    result = asyncio.run(call_tool("database", "get_product_details", {"product_id": 1}))
    assert result["structuredContent"]["ok"] is True
    assert result["structuredContent"]["product"]["id"] == 1

def test_invalid_inputs_are_structured_and_writes_require_approval():
    invalid = asyncio.run(call_tool("it_operations", "search_it_tickets", {"query": "x", "limit": 101}))
    assert invalid["structuredContent"]["ok"] is False
    assert invalid["structuredContent"]["error"]["code"] == "invalid_input"
    db = SessionLocal()
    try: before = db.query(Ticket).count()
    finally: db.close()
    denied = asyncio.run(call_tool("it_operations", "create_it_ticket", {
        "title": "Unauthorized test", "description": "This must not create a ticket", "severity": "low",
        "approval_id": 1, "authorization_token": "incorrect-token"}))
    db = SessionLocal()
    try: after = db.query(Ticket).count()
    finally: db.close()
    assert denied["structuredContent"]["ok"] is False
    assert denied["structuredContent"]["error"]["code"] == "unauthorized"
    assert before == after
