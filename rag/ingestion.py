"""Validated PDF/TXT ingestion into persistent semantic collections."""
from __future__ import annotations
import hashlib, re
from datetime import datetime, timezone
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import settings
from rag.vector_store import vector_store, VectorStoreError

SUPPORTED={".pdf",".txt"}
MAX_DOCUMENT_BYTES=10*1024*1024
class IngestionError(ValueError):pass
class DuplicateDocumentError(IngestionError):
    def __init__(self,document_id:str):super().__init__("This document has already been ingested"); self.document_id=document_id

def _clean(text:str)->str:
    text=text.replace("\x00", " ").replace("\r\n","\n").replace("\r","\n")
    text=re.sub(r"[\t\f\v]+"," ",text)
    text=re.sub(r"[ ]{2,}"," ",text)
    text=re.sub(r"\n[ \t]+","\n",text)
    text=re.sub(r"\n{3,}","\n\n",text)
    return text.strip()

def load_pages(path:Path)->list[tuple[int|None,str]]:
    suffix=path.suffix.lower()
    if suffix not in SUPPORTED:raise IngestionError("Only PDF and TXT documents are supported")
    try:
        if suffix==".txt":return [(None,_clean(path.read_text(encoding="utf-8-sig")))]
        from pypdf import PdfReader
        return [(i+1,_clean(page.extract_text() or "")) for i,page in enumerate(PdfReader(str(path)).pages)]
    except IngestionError:raise
    except Exception as exc:raise IngestionError(f"Could not read {suffix[1:].upper()} document ({type(exc).__name__})") from exc

def extract(path:Path)->str:
    return "\n\n".join(text for _,text in load_pages(path))

def _category(name:str,category:str|None)->str:
    if category:
        allowed={"ecommerce_policy","it_documentation","historical_incidents","general"}
        if category not in allowed:raise IngestionError(f"Category must be one of: {', '.join(sorted(allowed))}")
        return category
    low=name.lower()
    if "ecommerce" in low or "return" in low or "product_quality" in low:return "ecommerce_policy"
    if "incident" in low or "troubleshoot" in low or low.startswith("it_"):return "it_documentation"
    return "general"

def ingest_document(path:Path|str,category:str|None=None,*,upload_timestamp:str|None=None,document_name:str|None=None)->dict:
    path=Path(path)
    if not path.exists() or not path.is_file():raise IngestionError("Document file does not exist")
    if path.suffix.lower() not in SUPPORTED:raise IngestionError("Only PDF and TXT documents are supported")
    try:
        size=path.stat().st_size
        if size>MAX_DOCUMENT_BYTES:raise IngestionError("Document must be 10 MB or smaller")
        if size==0:raise IngestionError("Document is empty")
        raw=path.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    except OSError as exc:raise IngestionError("Could not read the uploaded document") from exc
    document_id=digest
    if vector_store.has_document(document_id):raise DuplicateDocumentError(document_id)
    pages=load_pages(path)
    if not any(text for _,text in pages):raise IngestionError("Document contains no extractable text")
    size_chunk=max(100,int(settings.rag_chunk_size)); overlap=max(0,min(int(settings.rag_chunk_overlap),size_chunk-1))
    splitter=RecursiveCharacterTextSplitter(chunk_size=size_chunk,chunk_overlap=overlap,add_start_index=True)
    display_name=document_name or path.name
    collection=_category(display_name,category)
    timestamp=upload_timestamp or datetime.now(timezone.utc).isoformat()
    chunks=[]
    for page_no,page_text in pages:
        if not page_text:continue
        for doc in splitter.create_documents([page_text]):
            text=doc.page_content.strip()
            if not text:continue
            chunk_idx=len(chunks)+1
            chunks.append({"text":text,"metadata":{"document_name":display_name,"document_id":document_id,"sha256":digest,"page_number":page_no,"chunk_id":chunk_idx,"start_index":doc.metadata.get("start_index"),"upload_timestamp":timestamp,"category":collection}})
    if not chunks:raise IngestionError("Document contains no extractable text")
    try:count=vector_store.add_chunks(chunks,collection)
    except Exception as exc:
        if isinstance(exc,IngestionError):raise
        raise IngestionError(f"Embedding or vector-store insertion failed ({type(exc).__name__})") from exc
    return {"document_id":document_id,"document_name":display_name,"category":collection,"chunks":count,"upload_timestamp":timestamp,"sha256":digest}

def ingest(path:Path)->int:
    """Phase 1 compatibility wrapper; returns inserted chunk count."""
    return ingest_document(path)["chunks"]
