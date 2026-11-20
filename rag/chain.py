"""Grounded document question answering with structured citations."""
from __future__ import annotations
import re
from pydantic import BaseModel, Field
from config import settings
from llm.provider import get_llm,get_active_provider,ProviderError
from llm.prompts import rag_prompt
from rag.retriever import retrieve_documents,format_retrieved_context,get_document_sources

class RAGResponse(BaseModel):
    answer:str
    sources:list[dict]=Field(default_factory=list)
    retrieval_count:int=0
    provider:str
    demo_mode:bool

class RAGChain:
    def invoke(self,payload:dict)->dict:
        return ask_question(payload.get("question",payload.get("query","")),domain=payload.get("domain"),top_k=payload.get("top_k"))

def create_rag_chain()->RAGChain:return RAGChain()

def _demo_answer(question:str,documents:list[dict])->str:
    if not documents:return "[SIMULATED DEMO RESPONSE] The indexed company documents do not contain information relevant to this question. No external LLM was called."
    # Quote retrieved evidence directly: no fabricated synthesis in keyless demo mode.
    excerpts=[]
    for i,item in enumerate(documents[:3],1):
        sentence=re.split(r"(?<=[.!?])\s+",item["text"].strip())[0]
        if sentence:excerpts.append(f"{sentence} [{i}]")
    return "[SIMULATED DEMO RESPONSE] Based only on retrieved document text: " + " ".join(excerpts) + " No external LLM was called."

def format_rag_response(answer:str,documents:list[dict],provider:str|None=None,demo_mode:bool|None=None)->RAGResponse:
    return RAGResponse(answer=answer,sources=get_document_sources(documents),retrieval_count=len(documents),provider=provider or get_active_provider(),demo_mode=settings.demo_mode if demo_mode is None else demo_mode)

def ask_question(question:str,domain:str|None=None,top_k:int|None=None)->dict:
    clean=question.strip()
    if not 3<=len(clean)<=2000:raise ValueError("Question must contain between 3 and 2000 characters")
    if domain not in {None,"ecommerce","it","it_operations","historical_incidents"}:raise ValueError("Domain must be ecommerce, it, or historical_incidents")
    documents=retrieve_documents(clean,top_k=top_k or settings.rag_top_k,domain=domain)
    if not documents:answer=_demo_answer(clean,documents) if settings.demo_mode else "The indexed company documents do not contain information relevant to this question."
    elif settings.demo_mode:answer=_demo_answer(clean,documents)
    else:
        context=format_retrieved_context(documents)
        try:answer=str(get_llm(temperature=0.0,max_tokens=800).invoke(rag_prompt(clean,context)).content)
        except ProviderError:raise
        except Exception as exc:raise ProviderError(f"RAG answer generation failed ({type(exc).__name__})") from exc
        # Only expose inline citation labels corresponding to sources returned in this response.
        max_citation=len(documents)
        answer=re.sub(r"\[(\d+)\]",lambda m:m.group(0) if int(m.group(1))<=max_citation else "",answer)
    return format_rag_response(answer,documents).model_dump()
