import importlib


def _reload_embeddings(monkeypatch, **env):
    for key in ("LLM_PROVIDER", "EMBED_PROVIDER", "EMBED_MODEL", "EMBED_DIM"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import agentic.memory.pg_vector.embeddings as embeddings

    return importlib.reload(embeddings)


def test_gemini_llm_provider_defaults_embedding_to_gemini(monkeypatch):
    embeddings = _reload_embeddings(monkeypatch, LLM_PROVIDER="gemini")

    assert embeddings.EMBED_PROVIDER == "gemini"
    assert embeddings.EMBED_MODEL == "gemini-embedding-001"
    assert embeddings.EMBED_DIM == 1536


def test_openai_embedding_defaults_stay_unchanged(monkeypatch):
    embeddings = _reload_embeddings(monkeypatch, LLM_PROVIDER="openai")

    assert embeddings.EMBED_PROVIDER == "openai"
    assert embeddings.EMBED_MODEL == "text-embedding-3-small"
    assert embeddings.EMBED_DIM == 1536


def test_local_llm_provider_defaults_embedding_to_ollama(monkeypatch):
    embeddings = _reload_embeddings(monkeypatch, LLM_PROVIDER="local")

    assert embeddings.EMBED_PROVIDER == "local"
    assert embeddings.EMBED_MODEL == "rjmalagon/gte-qwen2-1.5b-instruct-embed-f16"
    assert embeddings.EMBED_DIM == 1536


def test_fit_dimension_preserves_pgvector_schema(monkeypatch):
    embeddings = _reload_embeddings(monkeypatch, LLM_PROVIDER="gemini")

    assert embeddings._fit_dimension([1.0, 2.0], source="test")[:2] == [1.0, 2.0]
    assert len(embeddings._fit_dimension([1.0, 2.0], source="test")) == 1536
    assert embeddings._fit_dimension([1.0] * 1537, source="test") == [1.0] * 1536
