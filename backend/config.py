import os


class Settings:
    google_api_key: str = os.environ.get("GOOGLE_API_KEY", "")
    chroma_host: str = os.environ.get("CHROMA_HOST", "chromadb")
    chroma_port: int = int(os.environ.get("CHROMA_PORT", "8000"))
    vault_path: str = os.environ.get("VAULT_PATH", "/app/obsidian_vault")
    chroma_collection: str = os.environ.get("CHROMA_COLLECTION", "obsidian_docs")

    # RAG tunables
    similarity_threshold: float = float(os.environ.get("SIMILARITY_THRESHOLD", "0.6"))
    chunk_size: int = int(os.environ.get("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.environ.get("CHUNK_OVERLAP", "50"))

    # LLM tunables
    llm_model: str = os.environ.get("LLM_MODEL", "gemini-3-flash-preview")
    embedding_model: str = os.environ.get("EMBEDDING_MODEL", "models/gemini-embedding-2")
    llm_temperature: float = float(os.environ.get("LLM_TEMPERATURE", "0.2"))


settings = Settings()
