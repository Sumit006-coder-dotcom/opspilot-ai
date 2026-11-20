"""Domain-aware semantic retrieval and citation/context helpers."""
from pathlib import Path
import logging
from threading import Lock
from config import settings
from rag.vector_store import vector_store

ROOT=Path(__file__).resolve().parents[1]/"data"/"documents"
logger=logging.getLogger("operlynt.rag.retriever")
_INDEX_LOCK=Lock(); _DEMO_INDEXED=False
DOMAIN_COLLECTIONS={"ecommerce":"ecommerce_policy","it":"it_documentation","it_operations":"it_documentation","historical_incidents":"historical_incidents"}

def ensure_demo_documents_indexed()->None:
    global _DEMO_INDEXED
    if _DEMO_INDEXED:return
    with _INDEX_LOCK:
        if _DEMO_INDEXED:return
        if ROOT.exists():
            from rag.ingestion import ingest_document
            for path in ROOT.glob("*.txt"):
                if path.name.endswith(".chunks.txt"):continue
                try:ingest_document(path)
                except Exception as exc:
                    from rag.ingestion import DuplicateDocumentError
                    if not isinstance(exc,DuplicateDocumentError):raise
        _DEMO_INDEXED=True

def retrieve_documents(query:str,top_k:int|None=None,domain:str|None=None,metadata_filter:dict|None=None,threshold:float|None=None)->list[dict]:
    if not query.strip():return []
    logger.info("Ensuring bundled documents are indexed")
    ensure_demo_documents_indexed()
    logger.info("Bundled document check complete; resolving collections")
    scoped=DOMAIN_COLLECTIONS.get((domain or "").lower()) if domain else None
    filt=dict(metadata_filter or {})
    if domain in DOMAIN_COLLECTIONS:filt.setdefault("category",DOMAIN_COLLECTIONS[domain])
    limit=top_k or settings.rag_top_k
    score_threshold=settings.rag_similarity_threshold if threshold is None else threshold
    collections=[scoped] if scoped else ["ecommerce_policy","it_documentation","historical_incidents","general"]
    hits=[]
    for collection in collections:
        logger.info("Searching vector collection %s", collection)
        hits.extend(vector_store.search(query,k=limit,metadata_filter=filt or None,threshold=score_threshold,collection=collection))
    hits=sorted(hits,key=lambda h:h["score"],reverse=True)[:limit]
    result=[]
    for hit in hits:
        meta=hit["metadata"]
        result.append({"document":meta.get("document_name","unknown"),"document_id":meta.get("document_id"),"chunk":meta.get("chunk_id"),"page":meta.get("page_number"),"category":meta.get("category"),"upload_timestamp":meta.get("upload_timestamp"),"text":hit["text"],"score":hit["score"],"metadata":meta})
    return result

def format_retrieved_context(documents:list[dict])->str:
    blocks=[]
    for i,item in enumerate(documents,1):
        page=item.get("page")
        cite=f"{item.get('document','unknown')}"+(f", page {page}" if page else "")
        blocks.append(f"[{i}] Source: {cite}\n{item.get('text','')}")
    return "\n\n".join(blocks)

def get_document_sources(documents:list[dict])->list[dict]:
    sources=[]; seen=set()
    for i,item in enumerate(documents,1):
        key=(item.get("document_id"),item.get("page"),item.get("chunk"))
        if key in seen:continue
        seen.add(key)
        sources.append({"citation":i,"document_name":item.get("document","unknown"),"document_id":item.get("document_id"),"page_number":item.get("page"),"chunk_id":item.get("chunk"),"category":item.get("category"),"score":item.get("score")})
    return sources

def add_document(name:str,chunks:list[str])->None:
    """Compatibility helper: write chunks to a temporary text and persist semantically."""
    ROOT.mkdir(parents=True,exist_ok=True); path=ROOT/(name+".txt")
    path.write_text("\n\n".join(chunks),encoding="utf-8")
    from rag.ingestion import ingest_document
    ingest_document(path)

def search(query:str,limit:int=4)->list[dict]:
    return retrieve_documents(query,top_k=limit)
