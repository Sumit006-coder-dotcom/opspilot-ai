"""Cached Hugging Face sentence-transformers encoder with a LangChain interface."""
from __future__ import annotations
from functools import lru_cache
from typing import Sequence
from langchain_core.embeddings import Embeddings
from config import settings

DEFAULT_MODEL="sentence-transformers/all-MiniLM-L6-v2"
class EmbeddingError(RuntimeError): pass

def _selected_model(model_name:str|None)->str:return model_name or settings.embedding_model or DEFAULT_MODEL

@lru_cache(maxsize=2)
def load_embedding_model(model_name:str|None=None):
    model_name=_selected_model(model_name)
    try:
        from sentence_transformers import SentenceTransformer
        # Prefer a cached snapshot so offline environments do not perform avoidable HEAD calls.
        try:
            from huggingface_hub import snapshot_download
            local_path=snapshot_download(repo_id=model_name,local_files_only=True)
        except Exception:
            local_path=None
        if local_path:
            return SentenceTransformer(local_path,model_kwargs={"local_files_only":True},device="cpu")
        # First-use path: download through the Hugging Face cache, then reuse the model above.
        return SentenceTransformer(model_name,device="cpu")
    except Exception as exc:
        raise EmbeddingError(f"Could not load Hugging Face embedding model {model_name!r}; check the local model cache or network access ({type(exc).__name__})") from exc

def embed_documents(texts:Sequence[str],model_name:str|None=None)->list[list[float]]:
    if not texts: return []
    try:
        vectors=load_embedding_model(model_name).encode(list(texts),normalize_embeddings=True,show_progress_bar=False)
        return vectors.tolist()
    except EmbeddingError: raise
    except Exception as exc: raise EmbeddingError(f"Document embedding failed ({type(exc).__name__})") from exc

def embed_query(text:str,model_name:str|None=None)->list[float]:
    try:
        vector=load_embedding_model(model_name).encode([text],normalize_embeddings=True,show_progress_bar=False)[0]
        return vector.tolist()
    except EmbeddingError: raise
    except Exception as exc: raise EmbeddingError(f"Query embedding failed ({type(exc).__name__})") from exc

class HuggingFaceEmbeddings(Embeddings):
    """LangChain-compatible adapter over the cached local encoder."""
    def __init__(self,model_name:str|None=None): self.model_name=model_name or settings.embedding_model or DEFAULT_MODEL
    def embed_documents(self,texts:list[str])->list[list[float]]: return embed_documents(texts,self.model_name)
    def embed_query(self,text:str)->list[float]: return embed_query(text,self.model_name)
