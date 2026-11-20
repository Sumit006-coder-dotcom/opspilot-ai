import pytest
import sys
import types
from config import settings
from llm.provider import get_active_provider,get_llm,validate_provider_configuration,ProviderError,clear_provider_cache

def test_demo_provider_needs_no_key(monkeypatch):
    monkeypatch.setattr(settings,"demo_mode",True); monkeypatch.setattr(settings,"groq_api_key","")
    llm=get_llm(); response=llm.invoke("anything")
    assert "SIMULATED" in response.content and get_active_provider()=="demo"

def test_missing_provider_key_is_clear(monkeypatch):
    monkeypatch.setattr(settings,"demo_mode",False); monkeypatch.setattr(settings,"llm_provider","groq"); monkeypatch.setattr(settings,"groq_api_key","")
    with pytest.raises(ProviderError,match="GROQ_API_KEY"):validate_provider_configuration()

def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setattr(settings,"demo_mode",False); monkeypatch.setattr(settings,"llm_provider","other")
    with pytest.raises(ProviderError,match="LLM_PROVIDER"):validate_provider_configuration()

def test_openrouter_provider_selected_without_network(monkeypatch):
    class FakeChat:
        def __init__(self,**kwargs):self.kwargs=kwargs
        def with_retry(self,**kwargs):return self
    monkeypatch.setattr(settings,"demo_mode",False); monkeypatch.setattr(settings,"llm_provider","openrouter")
    monkeypatch.setattr(settings,"openrouter_api_key","test-key"); monkeypatch.setattr(settings,"openrouter_model","test/model")
    monkeypatch.setitem(sys.modules,"langchain_openai",types.SimpleNamespace(ChatOpenAI=FakeChat))
    clear_provider_cache()
    assert get_active_provider()=="openrouter" and get_llm().kwargs["base_url"]=="https://openrouter.ai/api/v1"
    clear_provider_cache()
