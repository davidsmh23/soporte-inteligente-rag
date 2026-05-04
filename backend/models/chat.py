from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class TriageRoute(str, Enum):
    RAG = "rag"
    FREE_CHAT = "free_chat"
    CONVERSATION = "conversation"


class Message(BaseModel):
    role: MessageRole
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


class ChatResponse(BaseModel):
    response: str
    route: TriageRoute
    sources: Optional[List[str]] = []
