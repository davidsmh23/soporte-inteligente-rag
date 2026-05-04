from fastapi import APIRouter, HTTPException

from models.knowledge import IndexResponse
from services.rag_service import index_vault

router = APIRouter()


@router.post("/index", response_model=IndexResponse)
def index_knowledge_base():
    try:
        return index_vault()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
