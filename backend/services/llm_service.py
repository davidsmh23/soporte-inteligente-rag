from langchain_google_genai import GoogleGenerativeAIEmbeddings

from backend.config import settings


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.embedding_api_key,
    )
