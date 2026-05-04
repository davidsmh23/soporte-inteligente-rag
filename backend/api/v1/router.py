from fastapi import APIRouter

from api.v1.chat import router as chat_router
from api.v1.knowledge import router as knowledge_router

api_router = APIRouter()
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
