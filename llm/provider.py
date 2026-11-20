"""Shared, credential-safe model-provider selection for Operlynt agents."""
from __future__ import annotations
from functools import lru_cache
from typing import Any
import time
from config import settings
from observability import emit_event

class ProviderError(RuntimeError):
    """Safe-to-display provider configuration or request failure."""

class SimulatedMessage:
    def __init__(self, content: str): self.content=content

class DemoLLM:
    """Deterministic demo model; it does not make a network request."""
    def invoke(self, prompt: str, **kwargs: Any) -> SimulatedMessage:
        return SimulatedMessage("[SIMULATED DEMO RESPONSE] No external LLM was called. Use retrieved context only; if it is missing, say the documents do not contain the answer.")

def get_active_provider() -> str:
    return "demo" if settings.demo_mode else settings.llm_provider.strip().lower()

def validate_provider_configuration() -> bool:
    if settings.demo_mode: return True
    provider=settings.llm_provider.strip().lower()
    if provider=="groq":
        if not settings.groq_api_key.strip(): raise ProviderError("GROQ_API_KEY is required when DEMO_MODE=false and LLM_PROVIDER=groq")
        if not settings.groq_model.strip(): raise ProviderError("GROQ_MODEL must not be empty")
    elif provider=="openrouter":
        if not settings.openrouter_api_key.strip(): raise ProviderError("OPENROUTER_API_KEY is required when DEMO_MODE=false and LLM_PROVIDER=openrouter")
        if not settings.openrouter_model.strip(): raise ProviderError("OPENROUTER_MODEL must not be empty")
    else: raise ProviderError("LLM_PROVIDER must be groq or openrouter")
    return True

@lru_cache(maxsize=1)
def _build_llm(provider: str, model_name: str, temperature: float, max_tokens: int):
    if provider=="groq":
        from langchain_groq import ChatGroq
        model=ChatGroq(api_key=settings.groq_api_key,model=model_name,temperature=temperature,max_tokens=max_tokens, max_retries=0)
    elif provider=="openrouter":
        from langchain_openai import ChatOpenAI
        model=ChatOpenAI(api_key=settings.openrouter_api_key,base_url="https://openrouter.ai/api/v1",model=model_name,temperature=temperature,max_tokens=max_tokens,max_retries=0)
    else: raise ProviderError("LLM_PROVIDER must be groq or openrouter")
    return model.with_retry(stop_after_attempt=3,wait_exponential_jitter=True)

def get_llm(*,temperature:float=0.0,max_tokens:int=800):
    """Return a cached LangChain chat model or deterministic no-key demo model."""
    if settings.demo_mode: return DemoLLM()
    validate_provider_configuration()
    name=settings.groq_model if settings.llm_provider.lower()=="groq" else settings.openrouter_model
    return _build_llm(settings.llm_provider.lower(),name,temperature,max_tokens)

def generate(prompt: str) -> dict:
    started=time.perf_counter()
    provider=get_active_provider()
    try:
        result=get_llm().invoke(prompt)
        usage=getattr(result,"usage_metadata",None) or getattr(result,"response_metadata",{}).get("token_usage",{})
        fields={"provider":provider,"duration_ms":round((time.perf_counter()-started)*1000,3),"status":"success"}
        if isinstance(usage,dict):
            for source,target in (("input_tokens","input_tokens"),("prompt_tokens","input_tokens"),("output_tokens","output_tokens"),("completion_tokens","output_tokens"),("total_tokens","total_tokens")):
                if source in usage: fields[target]=usage[source]
        emit_event("llm.request",**fields)
        return {"text":str(result.content),"simulated":settings.demo_mode,"provider":provider}
    except ProviderError as exc:
        emit_event("llm.error",level=__import__("logging").ERROR,provider=provider,duration_ms=round((time.perf_counter()-started)*1000,3),error_type=type(exc).__name__)
        raise
    except Exception as exc:
        emit_event("llm.error",level=__import__("logging").ERROR,provider=provider,duration_ms=round((time.perf_counter()-started)*1000,3),error_type=type(exc).__name__)
        name=type(exc).__name__.lower()
        if "rate" in name or "429" in str(exc): message="LLM provider rate limit reached; retry later"
        elif "timeout" in name or "connect" in name: message="LLM provider network request failed; check connectivity and retry"
        else: message=f"LLM provider request failed ({type(exc).__name__}); check provider configuration"
        raise ProviderError(message) from exc

def clear_provider_cache() -> None:
    """Clear model instances after in-process configuration changes (useful in tests)."""
    _build_llm.cache_clear()
