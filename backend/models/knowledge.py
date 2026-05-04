from pydantic import BaseModel


class IndexResponse(BaseModel):
    success: bool
    files_indexed: int
    chunks_indexed: int
    message: str
