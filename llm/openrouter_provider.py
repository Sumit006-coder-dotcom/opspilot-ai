"""OpenRouter provider entry point, retaining centralized settings and validation."""
from llm.provider import get_llm, validate_provider_configuration
def get_openrouter_llm(*,temperature:float=0.0,max_tokens:int=800):
    validate_provider_configuration()
    from config import settings
    if settings.llm_provider.lower()!="openrouter": raise ValueError("LLM_PROVIDER is not openrouter")
    return get_llm(temperature=temperature,max_tokens=max_tokens)
