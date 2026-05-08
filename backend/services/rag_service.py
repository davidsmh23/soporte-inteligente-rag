from pathlib import Path
import re
from functools import lru_cache
from typing import List

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings
from backend.models.chat import ChatResponse, Message, TriageRoute
from backend.models.knowledge import IndexResponse
from backend.models.rag import LookupMatch, LookupResponse
from backend.services.vectordb_service import get_vector_store


def index_vault() -> IndexResponse:
    loader = DirectoryLoader(
        settings.vault_path,
        glob="**/*.md",
        loader_cls=TextLoader,
    )
    documents = loader.load()

    if not documents:
        return IndexResponse(
            success=False,
            files_indexed=0,
            chunks_indexed=0,
            message="No se encontraron archivos .md en el vault.",
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(documents)
    get_vector_store().add_documents(chunks)

    return IndexResponse(
        success=True,
        files_indexed=len(documents),
        chunks_indexed=len(chunks),
        message=f"Se generaron {len(chunks)} embeddings desde {len(documents)} archivos.",
    )


def lookup_ticket(ticket_text: str, k: int | None = None, threshold: float | None = None) -> LookupResponse:
    effective_k = k if k is not None else settings.default_lookup_k
    effective_threshold = threshold if threshold is not None else settings.similarity_threshold

    results = get_vector_store().similarity_search_with_score(ticket_text, k=effective_k)
    matches = [_to_lookup_match(doc, score) for doc, score in results]

    is_known = bool(matches) and matches[0].score < effective_threshold
    route_hint = "resolved_with_reference" if is_known else "fallback_codex_chat"

    return LookupResponse(
        resolved=is_known,
        route_hint=route_hint,
        matches=matches,
    )


def process_chat(messages: List[Message]) -> ChatResponse:
    """
    Compatibility endpoint for previous /chat API contract.
    No generative LLM is used anymore: this returns deterministic guidance.
    """
    if not messages:
        return ChatResponse(
            response="No se recibieron mensajes.",
            route=TriageRoute.FREE_CHAT,
            sources=[],
        )

    lookup = lookup_ticket(messages[-1].content)

    if lookup.resolved:
        response_lines = [
            "Se ha encontrado una incidencia similar en la base de conocimiento.",
            "Referencia principal:",
            f"- {lookup.matches[0].source}",
            "",
            "Fragmento relevante:",
            lookup.matches[0].snippet,
        ]
        return ChatResponse(
            response="\n".join(response_lines),
            route=TriageRoute.RAG,
            sources=[m.source for m in lookup.matches],
        )

    route = TriageRoute.CONVERSATION if len(messages) > 1 else TriageRoute.FREE_CHAT
    return ChatResponse(
        response=(
            "No se ha encontrado una resolucion previa en ChromaDB. "
            "El flujo MCP/Codex CLI debe continuar con chat conversacional."
        ),
        route=route,
        sources=[],
    )


def _to_lookup_match(doc, score: float) -> LookupMatch:
    source_path = doc.metadata.get("source", "")
    source_name = Path(source_path).name if source_path else "unknown_source"
    snippet = _make_snippet(doc.page_content)
    metadata = {k: v for k, v in doc.metadata.items() if isinstance(k, str)}
    metadata["source_name"] = source_name
    source_text = _load_source_text(source_path) if source_path else doc.page_content
    case = _parse_case_fields(source_text or doc.page_content)

    return LookupMatch(
        source=source_name,
        score=float(score),
        snippet=snippet,
        ticket_id=case["ticket_id"],
        problem_title=case["problem_title"],
        solution_steps=case["solution_steps"],
        metadata=metadata,
    )


def _make_snippet(text: str, max_len: int = 600) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_len:
        return compact
    return compact[:max_len].rstrip() + "..."


def _parse_case_fields(text: str) -> dict:
    ticket_id = _extract_ticket_id(text)
    problem_title = _extract_problem_title(text)
    solution_steps = _extract_solution_steps(text)
    return {
        "ticket_id": ticket_id,
        "problem_title": problem_title,
        "solution_steps": solution_steps,
    }


def _extract_ticket_id(text: str) -> str | None:
    match = re.search(r"(?im)^\s*id_ticket\s*:\s*(#[0-9]+)\s*$", text)
    if match:
        return match.group(1).strip()
    return None


def _extract_problem_title(text: str) -> str | None:
    match = re.search(r"(?im)^\s*#\s*Problema\s*:\s*(.+?)\s*$", text)
    if match:
        return match.group(1).strip()
    return None


def _extract_solution_steps(text: str) -> List[str]:
    lines = text.splitlines()
    in_solution = False
    collected: List[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not in_solution:
            if re.match(r"(?i)^#\s*soluci[oó]n\s+exitosa\s*:\s*$", line):
                in_solution = True
            continue

        if re.match(r"^#\s+", line):
            break
        if line:
            collected.append(line)

    return collected


@lru_cache(maxsize=2048)
def _load_source_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
