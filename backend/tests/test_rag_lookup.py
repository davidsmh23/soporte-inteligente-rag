from types import SimpleNamespace

from backend.services import rag_service


class DummyVectorStore:
    def __init__(self, rows):
        self._rows = rows

    def similarity_search_with_score(self, _ticket_text, k=3):
        return self._rows[:k]


def _doc(source: str, content: str):
    return SimpleNamespace(metadata={"source": source}, page_content=content)


def test_lookup_ticket_resolved(monkeypatch):
    rows = [
        (_doc("/kb/error_postgres_conexiones.md", "solucion postgres"), 0.2),
        (_doc("/kb/otro.md", "otro"), 0.5),
    ]
    monkeypatch.setattr(rag_service, "get_vector_store", lambda: DummyVectorStore(rows))

    response = rag_service.lookup_ticket("postgres caido", k=3, threshold=0.6)

    assert response.resolved is True
    assert response.route_hint == "resolved_with_reference"
    assert response.matches[0].source == "error_postgres_conexiones.md"


def test_lookup_ticket_unresolved(monkeypatch):
    rows = [
        (_doc("/kb/error_postgres_conexiones.md", "solucion postgres"), 0.9),
    ]
    monkeypatch.setattr(rag_service, "get_vector_store", lambda: DummyVectorStore(rows))

    response = rag_service.lookup_ticket("incidencia nueva", k=3, threshold=0.6)

    assert response.resolved is False
    assert response.route_hint == "fallback_codex_chat"


def test_lookup_ticket_match_includes_ticket_fields(monkeypatch):
    markdown = """---
id_ticket: #2388
tecnologia: Docker
---
# Problema: Contenedor sale con error 1

# Solución Exitosa:
1. Revisar logs
2. Añadir DATABASE_URL
# Notas
Dato extra
"""
    rows = [
        (_doc("/kb/docker_contenedor_no_arranca.md", "chunk cualquiera"), 0.2),
    ]
    monkeypatch.setattr(rag_service, "get_vector_store", lambda: DummyVectorStore(rows))
    monkeypatch.setattr(rag_service, "_load_source_text", lambda _path: markdown)

    response = rag_service.lookup_ticket("docker compose up", k=3, threshold=0.6)

    assert response.matches[0].ticket_id == "#2388"
    assert response.matches[0].problem_title == "Contenedor sale con error 1"
    assert response.matches[0].solution_steps == [
        "1. Revisar logs",
        "2. Añadir DATABASE_URL",
    ]
