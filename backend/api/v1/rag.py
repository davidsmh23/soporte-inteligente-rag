from fastapi import APIRouter, HTTPException

from backend.models.rag import LookupRequest, LookupResponse
from backend.services.rag_service import lookup_ticket

router = APIRouter()


@router.post("/lookup", response_model=LookupResponse)
def lookup(request: LookupRequest):
    try:
        return lookup_ticket(
            ticket_text=request.ticket_text,
            k=request.k,
            threshold=request.threshold,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
