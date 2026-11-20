"""Company policy, technical documentation, and historical evidence MCP tools."""
from __future__ import annotations
import logging
from typing import Any
from mcp_servers.runtime import create_server, serve
from rag.retriever import retrieve_documents, get_document_sources

logger = logging.getLogger("operlynt.mcp.documents")
mcp = create_server("operlynt-documents")

def _search(query: str, domain: str) -> dict:
    clean = query.strip()
    if not 2 <= len(clean) <= 2000:
        return {"ok": False, "error": {"code": "invalid_input", "message": "query must contain 2 to 2000 characters."}}
    try:
        logger.info("Starting Phase 2 retrieval domain=%s", domain)
        docs = retrieve_documents(clean, top_k=4, domain=domain)
        logger.info("Completed Phase 2 retrieval domain=%s hits=%s", domain, len(docs))
        return {"ok": True, "domain": domain, "documents": docs, "sources": get_document_sources(docs)}
    except Exception as exc:
        logger.exception("Document MCP retrieval failed for domain=%s", domain)
        return {"ok": False, "error": {"code": "retrieval_error", "message": f"Document search failed ({type(exc).__name__})."}}

@mcp.tool(description="Search indexed e-commerce company policies and return source references.", structured_output=True)
async def search_company_policy(query: str) -> dict[str, Any]:
    return _search(query, "ecommerce")

@mcp.tool(description="Search indexed IT runbooks and technical documentation with source references.", structured_output=True)
async def search_technical_documentation(query: str) -> dict[str, Any]:
    return _search(query, "it")

@mcp.tool(description="Search historical incident documents and return source references.", structured_output=True)
async def search_historical_incidents(query: str) -> dict[str, Any]:
    return _search(query, "historical_incidents")

if __name__ == "__main__": serve(mcp)
