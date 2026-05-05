import asyncio
import json
import math
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Codex Session Gateway",
    version="2.0.0",
    description="Routes Streamlit user prompts to local Codex CLI agents via authenticated WebSocket.",
)


def _parse_user_tokens(raw: str) -> Dict[str, str]:
    token_map: Dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        user_id, token = pair.split(":", 1)
        token_map[user_id.strip()] = token.strip()
    return token_map


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock, self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    codex_session_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_message_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    codex_session_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    references_json TEXT NOT NULL,
                    token_usage_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_last ON conversations(user_id, last_message_at DESC);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_codex_created ON messages(codex_session_id, created_at);"
            )
            conn.commit()

    def create_pending_conversation(self, user_id: str, title: str, conversation_id: str | None = None) -> Dict[str, Any]:
        now = _now_iso()
        conv_id = (conversation_id or f"conv-{uuid.uuid4().hex[:12]}").strip()
        final_title = title.strip() if title and title.strip() else "Nueva conversación"
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations(conversation_id, user_id, codex_session_id, title, status, created_at, updated_at, last_message_at)
                VALUES(?, ?, NULL, ?, 'pending_bind', ?, ?, ?)
                """,
                (conv_id, user_id, final_title, now, now, now),
            )
            conn.commit()
        return {
            "conversation_id": conv_id,
            "user_id": user_id,
            "codex_session_id": None,
            "title": final_title,
            "status": "pending_bind",
            "created_at": now,
            "updated_at": now,
            "last_message_at": now,
        }

    def get_conversation(self, user_id: str, conversation_ref: str) -> Dict[str, Any] | None:
        ref = conversation_ref.strip()
        if not ref:
            return None
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM conversations
                WHERE user_id = ?
                  AND (conversation_id = ? OR codex_session_id = ?)
                LIMIT 1
                """,
                (user_id, ref, ref),
            ).fetchone()
        return dict(row) if row else None

    def bind_codex_session(self, user_id: str, conversation_id: str, codex_session_id: str) -> Dict[str, Any]:
        conv_id = conversation_id.strip()
        codex_id = codex_session_id.strip()
        if not conv_id or not codex_id:
            raise ValueError("conversation_id and codex_session_id are required")

        now = _now_iso()
        with self._lock, self._connect() as conn:
            existing_owner = conn.execute(
                """
                SELECT conversation_id, user_id
                FROM conversations
                WHERE codex_session_id = ?
                LIMIT 1
                """,
                (codex_id,),
            ).fetchone()
            if existing_owner and (
                existing_owner["conversation_id"] != conv_id or existing_owner["user_id"] != user_id
            ):
                raise ValueError("codex_session_id already belongs to another conversation")

            target = conn.execute(
                "SELECT * FROM conversations WHERE conversation_id = ? AND user_id = ? LIMIT 1",
                (conv_id, user_id),
            ).fetchone()
            if not target:
                raise ValueError("Conversation not found")

            conn.execute(
                """
                UPDATE conversations
                SET codex_session_id = ?,
                    status = 'active',
                    updated_at = ?
                WHERE conversation_id = ? AND user_id = ?
                """,
                (codex_id, now, conv_id, user_id),
            )
            conn.execute(
                """
                UPDATE messages
                SET codex_session_id = ?
                WHERE conversation_id = ? AND codex_session_id IS NULL
                """,
                (codex_id, conv_id),
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM conversations WHERE conversation_id = ? AND user_id = ? LIMIT 1",
                (conv_id, user_id),
            ).fetchone()

        if not row:
            raise ValueError("Conversation bind failed")
        return dict(row)

    def update_status(self, user_id: str, conversation_id: str, status: str):
        now = _now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE conversations
                SET status = ?, updated_at = ?
                WHERE conversation_id = ? AND user_id = ?
                """,
                (status, now, conversation_id, user_id),
            )
            conn.commit()

    def save_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        references: list[dict[str, Any]] | None = None,
        token_usage: dict[str, Any] | None = None,
    ):
        now = _now_iso()
        refs_json = json.dumps(references or [], ensure_ascii=False)
        token_json = json.dumps(token_usage, ensure_ascii=False) if isinstance(token_usage, dict) else None

        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT codex_session_id FROM conversations WHERE conversation_id = ? AND user_id = ? LIMIT 1",
                (conversation_id, user_id),
            ).fetchone()
            if not row:
                raise ValueError("Conversation not found")
            codex_id = row["codex_session_id"]

            conn.execute(
                """
                INSERT INTO messages(conversation_id, codex_session_id, role, content, references_json, token_usage_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, codex_id, role, content, refs_json, token_json, now),
            )
            conn.execute(
                """
                UPDATE conversations
                SET updated_at = ?, last_message_at = ?, status = CASE WHEN status = 'pending_bind' THEN 'pending_bind' ELSE 'active' END
                WHERE conversation_id = ? AND user_id = ?
                """,
                (now, now, conversation_id, user_id),
            )
            conn.commit()

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT conversation_id, codex_session_id, user_id, title, status, created_at, updated_at, last_message_at
                FROM conversations
                WHERE user_id = ?
                ORDER BY last_message_at DESC, created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_conversation_detail(self, user_id: str, conversation_ref: str) -> Dict[str, Any] | None:
        conversation = self.get_conversation(user_id, conversation_ref)
        if not conversation:
            return None

        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, references_json, token_usage_json, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation["conversation_id"],),
            ).fetchall()

        messages: list[dict[str, Any]] = []
        for row in rows:
            refs: list[dict[str, Any]] = []
            token_usage: dict[str, Any] | None = None
            try:
                refs = json.loads(row["references_json"] or "[]")
                if not isinstance(refs, list):
                    refs = []
            except json.JSONDecodeError:
                refs = []

            try:
                parsed_token = json.loads(row["token_usage_json"]) if row["token_usage_json"] else None
                token_usage = parsed_token if isinstance(parsed_token, dict) else None
            except json.JSONDecodeError:
                token_usage = None

            messages.append(
                {
                    "role": row["role"],
                    "content": row["content"],
                    "references": refs,
                    "token_usage": token_usage,
                    "created_at": row["created_at"],
                }
            )

        return {
            "conversation_id": conversation["conversation_id"],
            "codex_session_id": conversation.get("codex_session_id"),
            "user_id": conversation["user_id"],
            "title": conversation["title"],
            "status": conversation["status"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "last_message_at": conversation["last_message_at"],
            "messages": messages,
        }


USER_TOKENS = _parse_user_tokens(os.environ.get("SESSION_USER_TOKENS", "demo:demo-token"))
SHARED_TOKEN = os.environ.get("SESSION_SHARED_TOKEN", "")
SESSION_DB_PATH = os.environ.get("SESSION_DB_PATH", "/tmp/session_gateway_conversations.db")
STORE = ConversationStore(SESSION_DB_PATH)


@dataclass
class AgentConnection:
    user_id: str
    websocket: WebSocket
    queue: asyncio.Queue
    reader_task: asyncio.Task
    connected_at: datetime


class PromptRequest(BaseModel):
    user_id: str
    conversation_id: str | None = Field(default=None, max_length=128)
    codex_session_id: str | None = Field(default=None, max_length=128)
    # Backward compatibility field.
    session_id: str | None = Field(default=None, max_length=128)
    prompt: str = Field(min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)


class ConversationCreateRequest(BaseModel):
    user_id: str
    title: str | None = Field(default=None, max_length=200)


agents: Dict[str, AgentConnection] = {}
session_locks: Dict[str, asyncio.Lock] = {}


def _verify_token_for_user(user_id: str, token: str) -> bool:
    expected = USER_TOKENS.get(user_id)
    if expected:
        return token == expected
    if SHARED_TOKEN:
        return token == SHARED_TOKEN
    return False


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return authorization.split(" ", 1)[1].strip()


def _sse(event_type: str, data: Dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _estimate_tokens(text: str) -> int:
    content = str(text or "")
    if not content.strip():
        return 0
    return max(1, math.ceil(len(content) / 4))


def _build_token_usage(input_text: str, output_text: str) -> Dict[str, Any]:
    input_tokens = _estimate_tokens(input_text)
    output_tokens = _estimate_tokens(output_text)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "method": "chars_div_4_estimate",
    }


def _get_or_create_lock(user_id: str) -> asyncio.Lock:
    lock = session_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        session_locks[user_id] = lock
    return lock


async def _reader_loop(user_id: str, websocket: WebSocket, queue: asyncio.Queue):
    try:
        while True:
            message = await websocket.receive_json()
            if isinstance(message, dict):
                await queue.put(message)
    except WebSocketDisconnect:
        await queue.put({"type": "error", "code": "agent_disconnected", "request_id": None})
    except Exception as exc:
        await queue.put(
            {
                "type": "error",
                "code": "agent_reader_error",
                "message": str(exc),
                "request_id": None,
            }
        )
    finally:
        current = agents.get(user_id)
        if current and current.websocket is websocket:
            agents.pop(user_id, None)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/agents/{user_id}/status")
async def agent_status(user_id: str, authorization: str | None = Header(default=None)):
    token = _extract_bearer_token(authorization)
    if not _verify_token_for_user(user_id, token):
        raise HTTPException(status_code=401, detail="Invalid user token.")

    lock = _get_or_create_lock(user_id)
    connection = agents.get(user_id)
    return {
        "user_id": user_id,
        "connected": connection is not None,
        "busy": lock.locked(),
        "connected_at": connection.connected_at.isoformat() if connection else None,
    }


@app.post("/api/v1/conversations")
async def create_conversation(request: ConversationCreateRequest, authorization: str | None = Header(default=None)):
    token = _extract_bearer_token(authorization)
    if not _verify_token_for_user(request.user_id, token):
        raise HTTPException(status_code=401, detail="Invalid user token.")

    title = (request.title or "").strip() or "Nueva conversación"
    conversation = STORE.create_pending_conversation(user_id=request.user_id, title=title)
    return conversation


@app.get("/api/v1/conversations")
async def list_conversations(user_id: str = Query(...), authorization: str | None = Header(default=None)):
    token = _extract_bearer_token(authorization)
    if not _verify_token_for_user(user_id, token):
        raise HTTPException(status_code=401, detail="Invalid user token.")
    return {"conversations": STORE.list_conversations(user_id)}


@app.get("/api/v1/conversations/{conversation_ref}")
async def get_conversation(conversation_ref: str, user_id: str = Query(...), authorization: str | None = Header(default=None)):
    token = _extract_bearer_token(authorization)
    if not _verify_token_for_user(user_id, token):
        raise HTTPException(status_code=401, detail="Invalid user token.")

    detail = STORE.get_conversation_detail(user_id=user_id, conversation_ref=conversation_ref)
    if not detail:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return detail


@app.websocket("/ws/agent/{user_id}")
async def agent_ws(websocket: WebSocket, user_id: str):
    token = websocket.query_params.get("token", "")
    if not _verify_token_for_user(user_id, token):
        await websocket.close(code=1008, reason="Invalid token")
        return

    await websocket.accept()

    existing = agents.get(user_id)
    if existing:
        await existing.websocket.close(code=1012, reason="Replaced by a newer agent connection.")

    queue: asyncio.Queue = asyncio.Queue()
    reader_task = asyncio.create_task(_reader_loop(user_id, websocket, queue))
    agents[user_id] = AgentConnection(
        user_id=user_id,
        websocket=websocket,
        queue=queue,
        reader_task=reader_task,
        connected_at=datetime.now(timezone.utc),
    )

    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "server_ping"})
    except Exception:
        pass
    finally:
        reader_task.cancel()
        current = agents.get(user_id)
        if current and current.websocket is websocket:
            agents.pop(user_id, None)


@app.post("/api/v1/session/prompt")
async def submit_prompt(request: PromptRequest, authorization: str | None = Header(default=None)):
    token = _extract_bearer_token(authorization)
    if not _verify_token_for_user(request.user_id, token):
        raise HTTPException(status_code=401, detail="Invalid user token.")

    connection = agents.get(request.user_id)
    if not connection:
        raise HTTPException(status_code=503, detail="No Codex local agent is connected for this user.")

    lock = _get_or_create_lock(request.user_id)
    if lock.locked():
        raise HTTPException(status_code=409, detail="A prompt is already running for this user.")

    raw_conversation_ref = (request.conversation_id or request.session_id or "").strip()
    request_codex_session = (request.codex_session_id or "").strip() or None

    conversation = None
    if raw_conversation_ref:
        conversation = STORE.get_conversation(request.user_id, raw_conversation_ref)

    if not conversation and request_codex_session:
        conversation = STORE.get_conversation(request.user_id, request_codex_session)

    if not conversation:
        conversation = STORE.create_pending_conversation(
            user_id=request.user_id,
            title=(request.prompt.strip()[:80] or "Nueva conversación"),
            conversation_id=raw_conversation_ref or None,
        )

    conversation_id = conversation["conversation_id"]
    persisted_codex_session = conversation.get("codex_session_id")

    if persisted_codex_session and request_codex_session and persisted_codex_session != request_codex_session:
        raise HTTPException(
            status_code=409,
            detail="Conversation is already bound to another codex_session_id.",
        )

    if request_codex_session and not persisted_codex_session:
        try:
            conversation = STORE.bind_codex_session(
                user_id=request.user_id,
                conversation_id=conversation_id,
                codex_session_id=request_codex_session,
            )
            persisted_codex_session = conversation.get("codex_session_id")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    prompt_text = request.prompt.strip()
    try:
        STORE.save_message(
            user_id=request.user_id,
            conversation_id=conversation_id,
            role="user",
            content=prompt_text,
            references=[],
            token_usage=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    async def stream_events():
        stream_codex_session_id = persisted_codex_session
        async with lock:
            conn = agents.get(request.user_id)
            if not conn:
                yield _sse("error", {"type": "error", "message": "Agent disconnected before execution."})
                return

            while not conn.queue.empty():
                _ = conn.queue.get_nowait()

            request_id = str(uuid.uuid4())
            payload = {
                "type": "prompt",
                "request_id": request_id,
                "user_id": request.user_id,
                "conversation_id": conversation_id,
                "codex_session_id": stream_codex_session_id,
                "prompt": prompt_text,
                "history": request.history,
            }
            await conn.websocket.send_json(payload)
            yield _sse(
                "prompt_submitted",
                {
                    "type": "prompt_submitted",
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                },
            )

            saw_final = False
            accumulated = ""
            references: list[dict[str, Any]] = []
            assistant_token_usage: dict[str, Any] | None = None

            while True:
                try:
                    incoming = await asyncio.wait_for(conn.queue.get(), timeout=240)
                except asyncio.TimeoutError:
                    yield _sse(
                        "error",
                        {
                            "type": "error",
                            "request_id": request_id,
                            "message": "Timeout waiting for Codex local agent response.",
                        },
                    )
                    break

                incoming_request_id = incoming.get("request_id")
                if incoming_request_id not in {request_id, None}:
                    continue

                event_type = incoming.get("type", "message")
                if event_type == "token_delta":
                    delta = str(incoming.get("delta", ""))
                    accumulated += delta
                    yield _sse("token_delta", incoming)
                    continue

                if event_type == "tool_trace":
                    yield _sse("tool_trace", incoming)
                    continue

                if event_type == "mode_update":
                    yield _sse("mode_update", incoming)
                    continue

                if event_type == "conversation_bound":
                    bound_conversation_id = str(incoming.get("conversation_id") or conversation_id).strip()
                    bound_codex_session_id = str(incoming.get("codex_session_id") or "").strip()
                    if bound_conversation_id == conversation_id and bound_codex_session_id:
                        try:
                            conversation_row = STORE.bind_codex_session(
                                user_id=request.user_id,
                                conversation_id=conversation_id,
                                codex_session_id=bound_codex_session_id,
                            )
                            yield _sse(
                                "conversation_bound",
                                {
                                    "type": "conversation_bound",
                                    "conversation_id": conversation_row["conversation_id"],
                                    "codex_session_id": conversation_row["codex_session_id"],
                                },
                            )
                            stream_codex_session_id = conversation_row.get("codex_session_id")
                        except ValueError as exc:
                            yield _sse(
                                "error",
                                {
                                    "type": "error",
                                    "request_id": request_id,
                                    "message": f"conversation bind failed: {exc}",
                                },
                            )
                    continue

                if event_type == "final_answer":
                    incoming_codex_session = str(incoming.get("codex_session_id") or "").strip()
                    if incoming_codex_session and not stream_codex_session_id:
                        try:
                            conversation_row = STORE.bind_codex_session(
                                user_id=request.user_id,
                                conversation_id=conversation_id,
                                codex_session_id=incoming_codex_session,
                            )
                            stream_codex_session_id = conversation_row.get("codex_session_id")
                            yield _sse(
                                "conversation_bound",
                                {
                                    "type": "conversation_bound",
                                    "conversation_id": conversation_row["conversation_id"],
                                    "codex_session_id": conversation_row["codex_session_id"],
                                },
                            )
                        except ValueError:
                            pass

                    if incoming.get("answer"):
                        accumulated = str(incoming["answer"])
                    references = incoming.get("references", []) or []
                    if not isinstance(incoming.get("token_usage"), dict):
                        incoming["token_usage"] = _build_token_usage(prompt_text, accumulated)
                    assistant_token_usage = incoming.get("token_usage")
                    saw_final = True
                    yield _sse("final_answer", incoming)
                    break

                if event_type == "error":
                    code = str(incoming.get("code") or "").strip()
                    if code == "agent_unavailable":
                        STORE.update_status(
                            user_id=request.user_id,
                            conversation_id=conversation_id,
                            status="agent_unavailable",
                        )
                    yield _sse("error", incoming)
                    break

                yield _sse("message", incoming)

            if not saw_final and accumulated:
                assistant_token_usage = _build_token_usage(prompt_text, accumulated)
                payload_final = {
                    "type": "final_answer",
                    "request_id": request_id,
                    "answer": accumulated,
                    "references": references,
                    "token_usage": assistant_token_usage,
                }
                yield _sse("final_answer", payload_final)

            if saw_final or accumulated:
                try:
                    STORE.save_message(
                        user_id=request.user_id,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=accumulated.strip(),
                        references=references,
                        token_usage=assistant_token_usage,
                    )
                    STORE.update_status(
                        user_id=request.user_id,
                        conversation_id=conversation_id,
                        status="active",
                    )
                except ValueError:
                    pass

    return StreamingResponse(stream_events(), media_type="text/event-stream")
