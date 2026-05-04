import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Codex Session Gateway",
    version="1.0.0",
    description="Routes Streamlit user prompts to local Codex CLI agents via authenticated WebSocket.",
)


def _parse_user_tokens(raw: str) -> Dict[str, str]:
    # Format: "user1:token1,user2:token2"
    token_map: Dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        user_id, token = pair.split(":", 1)
        token_map[user_id.strip()] = token.strip()
    return token_map


USER_TOKENS = _parse_user_tokens(os.environ.get("SESSION_USER_TOKENS", "demo:demo-token"))
SHARED_TOKEN = os.environ.get("SESSION_SHARED_TOKEN", "")


@dataclass
class AgentConnection:
    user_id: str
    websocket: WebSocket
    queue: asyncio.Queue
    reader_task: asyncio.Task
    connected_at: datetime


class PromptRequest(BaseModel):
    user_id: str
    session_id: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)


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
            # Keep websocket alive and consume incoming messages in reader task.
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

    async def stream_events():
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
                "session_id": request.session_id,
                "prompt": request.prompt,
                "history": request.history,
            }
            await conn.websocket.send_json(payload)
            yield _sse("prompt_submitted", {"type": "prompt_submitted", "request_id": request_id})

            saw_final = False
            accumulated = ""
            references: list[dict[str, Any]] = []

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

                if event_type == "final_answer":
                    if incoming.get("answer"):
                        accumulated = str(incoming["answer"])
                    references = incoming.get("references", []) or []
                    saw_final = True
                    yield _sse("final_answer", incoming)
                    break

                if event_type == "error":
                    yield _sse("error", incoming)
                    break

                yield _sse("message", incoming)

            if not saw_final and accumulated:
                yield _sse(
                    "final_answer",
                    {
                        "type": "final_answer",
                        "request_id": request_id,
                        "answer": accumulated,
                        "references": references,
                    },
                )

    return StreamingResponse(stream_events(), media_type="text/event-stream")
