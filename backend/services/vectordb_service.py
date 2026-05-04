from langchain_community.vectorstores import Chroma
import chromadb

from config import settings
from services.llm_service import get_embeddings


def get_chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def get_vector_store() -> Chroma:
    client = get_chroma_client()
    return Chroma(
        client=client,
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
    )
