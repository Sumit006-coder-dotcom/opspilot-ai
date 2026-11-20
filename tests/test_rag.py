from rag.chain import ask_question,format_rag_response
import rag.chain as chain

def test_demo_rag_answer_is_grounded_and_structured(monkeypatch):
    docs=[{"document":"return_policy.txt","document_id":"abc","chunk":1,"page":2,"category":"ecommerce_policy","text":"Defective goods qualify for a prepaid return label.","score":0.8}]
    monkeypatch.setattr(chain,"retrieve_documents",lambda *a,**k:docs)
    result=ask_question("What happens to defective goods?",domain="ecommerce")
    assert result["demo_mode"] is True and result["provider"]=="demo"
    assert result["retrieval_count"]==1 and result["sources"][0]["page_number"]==2
    assert "prepaid return label" in result["answer"] and "[1]" in result["answer"]

def test_empty_retrieval_says_unavailable(monkeypatch):
    monkeypatch.setattr(chain,"retrieve_documents",lambda *a,**k:[])
    result=ask_question("What is the moon policy?")
    assert result["sources"]==[] and "do not contain" in result["answer"]
