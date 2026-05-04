from fastapi import APIRouter

from backend.api.v1.chat import router as chat_router
from backend.api.v1.knowledge import router as knowledge_router
from backend.api.v1.rag import router as rag_router

api_router = APIRouter()
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
