from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LookupRequest(BaseModel):
    ticket_text: str
    k: int = Field(default=3, ge=1, le=10)
    threshold: Optional[float] = Field(default=None, ge=0.0)


class LookupMatch(BaseModel):
    source: str
    score: float
    snippet: str
    ticket_id: Optional[str] = None
    problem_title: Optional[str] = None
    solution_steps: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LookupResponse(BaseModel):
    resolved: bool
    route_hint: str
    matches: List[LookupMatch] = Field(default_factory=list)
