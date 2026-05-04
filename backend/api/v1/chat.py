from fastapi import APIRouter, HTTPException

from backend.models.chat import ChatRequest, ChatResponse
from backend.services.rag_service import process_chat

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        return process_chat(request.messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
