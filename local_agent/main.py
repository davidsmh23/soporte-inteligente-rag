import asyncio
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import websockets

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None

SESSION_GATEWAY_WS_URL = os.environ.get("SESSION_GATEWAY_WS_URL", "ws://localhost:9000/ws/agent")
SESSION_USER_ID = os.environ.get("SESSION_USER_ID", "demo")
SESSION_USER_TOKEN = os.environ.get("SESSION_USER_TOKEN", "demo-token")
CODEX_EXEC_TIMEOUT_SEC = int(os.environ.get("CODEX_EXEC_TIMEOUT_SEC", "300"))
DIAGNOSTIC_VERBOSE = os.environ.get("DIAGNOSTIC_VERBOSE", "1").strip() not in {"0", "false", "False"}

SESSION_MODE_CHAT = "chat_generico"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
UUID_INLINE_RE = re.compile(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})")


def _count_tokens(text: str) -> tuple[int, str]:
    content = str(text or "")
    if not content.strip():
        return 0, "empty"

    if tiktoken is not None:
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(content)), "tiktoken_cl100k_base"
        except Exception:
            pass

    return max(1, math.ceil(len(content) / 4)), "chars_div_4_estimate"


def _build_token_usage(input_text: str, output_text: str) -> dict[str, Any]:
    input_tokens, input_method = _count_tokens(input_text)
    output_tokens, output_method = _count_tokens(output_text)
    method = input_method if input_method == output_method else f"{input_method}+{output_method}"
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "method": method,
    }


def _prompt_preview(prompt: str, max_len: int = 600) -> str:
    compact = " ".join(str(prompt or "").split())
    if len(compact) <= max_len:
        return compact
    return compact[:max_len].rstrip() + "..."


def _extract_text(event: Any) -> str:
    if isinstance(event, str):
        return event
    if isinstance(event, list):
        parts = [_extract_text(item) for item in event]
        return " ".join(part for part in parts if part).strip()
    if isinstance(event, dict):
        if isinstance(event.get("content"), str):
            return event["content"]
        if isinstance(event.get("text"), str):
            return event["text"]
        if isinstance(event.get("delta"), str):
            return event["delta"]
        if "msg" in event:
            return _extract_text(event["msg"])
        payload = event.get("payload")
        if isinstance(payload, dict):
            payload_text = _extract_text(payload)
            if payload_text:
                return payload_text
    return ""


def _find_uuid(value: Any) -> str | None:
    if isinstance(value, str) and UUID_RE.match(value.strip()):
        return value.strip()
    if isinstance(value, dict):
        for key in ("thread_id", "session_id", "id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and UUID_RE.match(candidate.strip()):
                return candidate.strip()
        for nested in value.values():
            found = _find_uuid(nested)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_uuid(item)
            if found:
                return found
    return None


def _extract_thread_id(event: Any) -> str | None:
    if not isinstance(event, dict):
        return None

    event_type = str(event.get("type") or "")
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else None

    if payload:
        payload_type = str(payload.get("type") or "")
        if payload_type in {"thread.started", "thread_name_updated", "thread.updated"}:
            return _find_uuid(payload)

    if event_type in {"thread.started", "thread_name_updated", "thread.updated"}:
        return _find_uuid(event)

    return _find_uuid(event)


def _extract_uuid_from_text(text: str) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    # Avoid binding to arbitrary UUIDs from diagnostics/errors; only accept
    # explicit session continuation hints.
    if "codex resume" not in lowered and "thread.started" not in lowered and "thread_id" not in lowered:
        return None
    match = UUID_INLINE_RE.search(text)
    if not match:
        return None
    candidate = match.group(1).strip()
    return candidate if UUID_RE.match(candidate) else None


def _normalize_codex_session_id(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in {"none", "null", "undefined"}:
        return None
    if UUID_RE.match(raw):
        return raw
    return None


def _session_index_path() -> Path:
    return Path.home() / ".codex" / "session_index.jsonl"


def _read_recent_session_ids(limit: int = 200) -> list[str]:
    path = _session_index_path()
    if not path.exists():
        return []

    ids: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for raw in lines[-limit:]:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            candidate = obj.get("id")
            if isinstance(candidate, str) and UUID_RE.match(candidate.strip()):
                ids.append(candidate.strip())
    except OSError:
        return []

    return ids


def _get_new_session_id(before: list[str], after: list[str]) -> str | None:
    before_set = set(before)
    for candidate in reversed(after):
        if candidate not in before_set:
            return candidate
    return None


async def _trace(websocket, request_id: str, detail: str, *, force: bool = False):
    if not (DIAGNOSTIC_VERBOSE or force):
        return
    await websocket.send(
        json.dumps(
            {
                "type": "tool_trace",
                "request_id": request_id,
                "detail": detail,
            }
        )
    )


def _mode_label(mode: str) -> str:
    labels = {
        SESSION_MODE_CHAT: "Chat generico",
    }
    return labels.get(mode, mode)


async def _send_mode_update(websocket, request_id: str, conversation_id: str, mode: str):
    await websocket.send(
        json.dumps(
            {
                "type": "mode_update",
                "request_id": request_id,
                "conversation_id": conversation_id,
                "mode": mode,
                "label": _mode_label(mode),
            }
        )
    )


def _resolve_codex_bin() -> str | None:
    explicit = os.environ.get("CODEX_BIN", "").strip()
    if explicit and Path(explicit).exists():
        return explicit

    for candidate in ["codex", "codex.exe"]:
        path = shutil.which(candidate)
        if path:
            return path
    return None


async def _run_codex_and_stream(
    websocket,
    request_id: str,
    conversation_id: str,
    prompt: str,
    codex_session_id: str | None,
):
    codex_bin = _resolve_codex_bin()
    if not codex_bin:
        await websocket.send(
            json.dumps(
                {
                    "type": "error",
                    "request_id": request_id,
                    "message": "No se encontro el binario 'codex' en el cliente local.",
                }
            )
        )
        return

    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        await websocket.send(
            json.dumps(
                {
                    "type": "error",
                    "request_id": request_id,
                    "message": "Prompt vacio.",
                }
            )
        )
        return

    known_session = _normalize_codex_session_id(codex_session_id)
    output_path = None
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as output_file:
        output_path = output_file.name

    before_sessions = _read_recent_session_ids() if not known_session else []

    if known_session:
        cmd = [
            codex_bin,
            "exec",
            "resume",
            "--json",
            "-o",
            output_path,
            known_session,
            prompt_text,
        ]
    else:
        cmd = [
            codex_bin,
            "exec",
            "--json",
            "-o",
            output_path,
            prompt_text,
        ]

    await _trace(websocket, request_id, f"[prompt_preview] {_prompt_preview(prompt_text)}", force=True)
    await _trace(websocket, request_id, f"[codex_cmd] {' '.join(cmd[:7])} ...", force=True)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    accumulated = ""
    streamed_events = 0
    detected_thread_id = known_session

    try:
        while True:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=CODEX_EXEC_TIMEOUT_SEC)
            if not line:
                break

            raw = line.decode("utf-8", errors="replace").strip()
            if not raw:
                continue

            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                event = {"type": "text", "content": raw}

            if not detected_thread_id:
                detected_thread_id = _extract_thread_id(event)
                if not detected_thread_id:
                    detected_thread_id = _extract_uuid_from_text(raw)
                if detected_thread_id:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "conversation_bound",
                                "request_id": request_id,
                                "conversation_id": conversation_id,
                                "codex_session_id": detected_thread_id,
                            }
                        )
                    )

            event_text = _extract_text(event)
            if event_text:
                accumulated += event_text + "\n"
                streamed_events += 1
                await websocket.send(
                    json.dumps(
                        {
                            "type": "token_delta",
                            "request_id": request_id,
                            "delta": event_text + "\n",
                        }
                    )
                )

        return_code = await process.wait()
        stderr_text = (await process.stderr.read()).decode("utf-8", errors="replace")
        await _trace(
            websocket,
            request_id,
            f"[codex_exit] code={return_code} streamed_events={streamed_events}",
            force=True,
        )

        if stderr_text.strip():
            await _trace(websocket, request_id, f"[codex_stderr] {stderr_text[:1500]}")

        if not detected_thread_id and not known_session:
            after_sessions = _read_recent_session_ids()
            fallback_thread = _get_new_session_id(before_sessions, after_sessions)
            if fallback_thread:
                detected_thread_id = fallback_thread
                await websocket.send(
                    json.dumps(
                        {
                            "type": "conversation_bound",
                            "request_id": request_id,
                            "conversation_id": conversation_id,
                            "codex_session_id": detected_thread_id,
                        }
                    )
                )

        if return_code != 0:
            lowered = f"{stderr_text} {accumulated}".lower()
            is_resume_error = bool(known_session) and (
                "resume" in lowered and ("not found" in lowered or "no session" in lowered)
                or "unknown session" in lowered
                or "invalid session" in lowered
            )
            payload = {
                "type": "error",
                "request_id": request_id,
                "message": f"codex exec fallo con codigo {return_code}: {stderr_text[:2000]}",
            }
            if is_resume_error:
                payload["code"] = "agent_unavailable"
                payload["message"] = (
                    "La sesion de Codex no esta disponible en este agente local. "
                    "Conecta el agente original para continuar esta conversacion."
                )
            await websocket.send(json.dumps(payload))
            return

        final_answer = accumulated.strip()
        try:
            if output_path and os.path.exists(output_path):
                output_text = Path(output_path).read_text(encoding="utf-8", errors="replace").strip()
                if output_text:
                    final_answer = output_text
        except OSError:
            pass

        usage = _build_token_usage(prompt_text, final_answer)
        await websocket.send(
            json.dumps(
                {
                    "type": "final_answer",
                    "request_id": request_id,
                    "answer": final_answer,
                    "references": [],
                    "token_usage": usage,
                    "codex_session_id": detected_thread_id,
                }
            )
        )
    except asyncio.TimeoutError:
        process.kill()
        await websocket.send(
            json.dumps(
                {
                    "type": "error",
                    "request_id": request_id,
                    "message": "Timeout en ejecucion de codex exec.",
                }
            )
        )
    finally:
        if output_path:
            try:
                os.remove(output_path)
            except OSError:
                pass


async def _run_once():
    ws_url = f"{SESSION_GATEWAY_WS_URL.rstrip('/')}/{SESSION_USER_ID}?token={SESSION_USER_TOKEN}"
    async with websockets.connect(ws_url, max_size=None, ping_interval=20, ping_timeout=20) as websocket:
        while True:
            raw = await websocket.recv()
            message = json.loads(raw)
            if message.get("type") == "server_ping":
                continue
            if message.get("type") != "prompt":
                continue

            request_id = str(message.get("request_id", "")).strip()
            prompt = str(message.get("prompt", "")).strip()
            conversation_id = str(message.get("conversation_id", "")).strip() or "default-conversation"
            codex_session_id = _normalize_codex_session_id(message.get("codex_session_id"))

            await _send_mode_update(
                websocket,
                request_id=request_id,
                conversation_id=conversation_id,
                mode=SESSION_MODE_CHAT,
            )
            await _run_codex_and_stream(
                websocket,
                request_id=request_id,
                conversation_id=conversation_id,
                prompt=prompt,
                codex_session_id=codex_session_id,
            )


async def main():
    retry_delay = 3
    while True:
        try:
            await _run_once()
            retry_delay = 3
        except Exception:
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)


if __name__ == "__main__":
    asyncio.run(main())
