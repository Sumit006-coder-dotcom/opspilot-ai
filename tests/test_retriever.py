from rag.vector_store import VectorStore
from rag.retriever import retrieve_documents,format_retrieved_context,get_document_sources
from tests.fakes import FakeEmbeddings
import rag.retriever as retriever

def test_semantic_search_filter_and_citations(tmp_path,monkeypatch):
    store=VectorStore(tmp_path,FakeEmbeddings())
    store.add_chunks([
        {"text":"Defective product returns are accepted within thirty days.","metadata":{"document_name":"returns.txt","document_id":"e1","page_number":None,"chunk_id":1,"category":"ecommerce_policy"}},
        {"text":"Critical incidents require immediate escalation.","metadata":{"document_name":"it.txt","document_id":"i1","page_number":3,"chunk_id":1,"category":"it_documentation"}},
    ],"ecommerce_policy")
    store.add_chunks([{"text":"Critical incidents require immediate escalation.","metadata":{"document_name":"it.txt","document_id":"i1","page_number":3,"chunk_id":1,"category":"it_documentation"}}],"it_documentation")
    monkeypatch.setattr(retriever,"vector_store",store); monkeypatch.setattr(retriever,"_DEMO_INDEXED",True)
    hits=retrieve_documents("defective product return",domain="ecommerce")
    assert hits[0]["document"]=="returns.txt"
    assert "[1] Source: returns.txt" in format_retrieved_context(hits)
    assert get_document_sources(hits)[0]["document_name"]=="returns.txt"
    assert retrieve_documents("unrelated astrophysics question",domain="ecommerce",threshold=0.95)==[]

def test_faiss_persists_across_store_instances(tmp_path):
    store=VectorStore(tmp_path,FakeEmbeddings())
    store.add_chunks([{"text":"Refunds for defective goods are available.","metadata":{"document_name":"policy.txt","document_id":"persist-me","chunk_id":1,"category":"ecommerce_policy"}}],"ecommerce_policy")
    restarted=VectorStore(tmp_path,FakeEmbeddings())
    hits=restarted.search("defective goods refund",collection="ecommerce_policy")
    assert hits and hits[0]["metadata"]["document_id"]=="persist-me"
    assert restarted.list_documents()[0]["chunk_count"]==1
