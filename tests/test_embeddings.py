import os

import pytest
import numpy as np

from rag.embeddings import HuggingFaceEmbeddings, embed_documents,embed_query,load_embedding_model


def test_huggingface_adapter_uses_embedding_model(monkeypatch):
    class FakeModel:
        def encode(self, texts, **_kwargs):
            return np.asarray([[1.0, 0.0] for _ in texts], dtype="float32")
    monkeypatch.setattr("rag.embeddings.load_embedding_model", lambda _name=None: FakeModel())
    adapter = HuggingFaceEmbeddings("test-model")
    assert adapter.embed_documents(["one", "two"]) == [[1.0, 0.0], [1.0, 0.0]]
    assert adapter.embed_query("one") == [1.0, 0.0]


@pytest.mark.skipif(os.getenv("RUN_HF_MODEL_TESTS") != "1", reason="set RUN_HF_MODEL_TESTS=1 to run the model-download integration test")
def test_huggingface_embedding_generation_and_cache():
    load_embedding_model.cache_clear()
    vectors=embed_documents(["return defective product","critical incident escalation"])
    query=embed_query("return product")
    assert len(vectors)==2 and len(vectors[0])==len(query)>0
    assert abs(sum(v*v for v in query)-1)<0.02
    assert load_embedding_model.cache_info().hits>=1
