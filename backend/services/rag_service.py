from pathlib import Path
from typing import List

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings
from backend.models.chat import ChatResponse, Message, MessageRole, TriageRoute
from backend.models.knowledge import IndexResponse
from backend.services.llm_service import get_llm
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


def process_chat(messages: List[Message]) -> ChatResponse:
    llm = get_llm()
    last_message = messages[-1].content

    if len(messages) == 1:
        return _triage(last_message, llm)

    return _continue_conversation(messages, llm)


# --- rutas de triage ---

def _triage(ticket: str, llm) -> ChatResponse:
    vector_store = get_vector_store()
    results = vector_store.similarity_search_with_score(ticket, k=3)

    is_known = bool(results) and results[0][1] < settings.similarity_threshold

    if is_known:
        return _rag_response(ticket, results, llm)
    return _free_chat_response(ticket, llm)


def _rag_response(ticket: str, results, llm) -> ChatResponse:
    context = "\n\n".join(doc.page_content for doc, _ in results)
    sources = [Path(doc.metadata.get("source", "")).name for doc, _ in results]

    system_prompt = (
        "Eres un asistente de soporte técnico experto. "
        "Usa los siguientes fragmentos de contexto de Obsidian para resolver el ticket. "
        "Explica la solución claramente y cita el nombre del archivo al final.\n\n"
        f"Contexto recuperado:\n{context}"
    )

    chain = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ]) | llm

    return ChatResponse(
        response=chain.invoke({"input": ticket}).content,
        route=TriageRoute.RAG,
        sources=sources,
    )


def _free_chat_response(ticket: str, llm) -> ChatResponse:
    system_prompt = (
        "Eres un asistente de soporte técnico avanzado. "
        "El agente acaba de introducir un ticket que NO está en la base de datos de conocimiento. "
        "Admite que parece un problema nuevo y guía al agente paso a paso para hacer debug "
        "o pedir más información (logs, configuraciones)."
    )

    chain = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ]) | llm

    return ChatResponse(
        response=chain.invoke({"input": ticket}).content,
        route=TriageRoute.FREE_CHAT,
        sources=[],
    )


def _continue_conversation(messages: List[Message], llm) -> ChatResponse:
    history = [
        SystemMessage(content="Eres un asistente de soporte técnico. Continúa ayudando al agente a resolver el problema.")
    ]

    for msg in messages[:-1]:
        if msg.role == MessageRole.USER:
            history.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            history.append(AIMessage(content=msg.content))

    history.append(HumanMessage(content=messages[-1].content))

    return ChatResponse(
        response=llm.invoke(history).content,
        route=TriageRoute.CONVERSATION,
        sources=[],
    )
