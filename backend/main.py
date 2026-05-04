from fastapi import FastAPI

from api.v1.router import api_router

app = FastAPI(
    title="Soporte Inteligente API",
    description="Backend RAG para el asistente de soporte técnico",
    version="2.0.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
