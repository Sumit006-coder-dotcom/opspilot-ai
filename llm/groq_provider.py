"""Groq provider entry point, retaining centralized settings and validation."""
from llm.provider import get_llm, validate_provider_configuration
def get_groq_llm(*,temperature:float=0.0,max_tokens:int=800):
    validate_provider_configuration()
    from config import settings
    if settings.llm_provider.lower()!="groq": raise ValueError("LLM_PROVIDER is not groq")
    return get_llm(temperature=temperature,max_tokens=max_tokens)
