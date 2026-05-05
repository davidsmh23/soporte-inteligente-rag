import asyncio
import json
import os
import re
import shutil
import tempfile
import math
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

import websockets
try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None

SESSION_GATEWAY_WS_URL = os.environ.get("SESSION_GATEWAY_WS_URL", "ws://localhost:9000/ws/agent")
SESSION_USER_ID = os.environ.get("SESSION_USER_ID", "demo")
SESSION_USER_TOKEN = os.environ.get("SESSION_USER_TOKEN", "demo-token")
CODEX_EXEC_TIMEOUT_SEC = int(os.environ.get("CODEX_EXEC_TIMEOUT_SEC", "300"))
SUPPORT_MCP_URL = os.environ.get("SUPPORT_MCP_URL", "http://localhost:8100/mcp")
SUPPORT_MCP_TOKEN = os.environ.get("SUPPORT_MCP_TOKEN", "")
DIAGNOSTIC_VERBOSE = os.environ.get("DIAGNOSTIC_VERBOSE", "1").strip() not in {"0", "false", "False"}

SESSION_MODE_TRIAGE = "triage_inicial"
SESSION_MODE_CHAT = "chat_generico"
SESSION_MODE_RESOLVED = "resuelto_por_referencia"


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

    # Conservative fallback when tokenizer is not available.
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


def _load_env_value(key: str) -> str:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return ""
    try:
        for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip().strip("'\"")
    except OSError:
        return ""
    return ""


if not SUPPORT_MCP_TOKEN:
    SUPPORT_MCP_TOKEN = _load_env_value("MCP_BEARER_TOKEN")


def _build_chat_prompt(
    ticket_text: str,
    history: list[dict[str, Any]],
) -> str:
    cleaned = ticket_text.strip()
    if not cleaned:
        return ""

    prev_user, prev_assistant = _last_turn_pair(history, current_user_message=cleaned)

    # Default: direct prompt (closest behavior to Codex CLI chat).
    if not _looks_followup(cleaned):
        return cleaned

    if not prev_user and not prev_assistant:
        return cleaned

    rewritten = _rewrite_followup_as_standalone(prev_user, cleaned)
    return rewritten or cleaned


def _looks_followup(text: str) -> bool:
    lowered = text.lower().strip()
    if lowered.startswith("y "):
        return True
    if lowered in {"y?", "y", "y eso?", "y luego?"}:
        return True
    return len(lowered) <= 40 and lowered.startswith(("y ", "tambien ", "y en "))


def _rewrite_followup_as_standalone(prev_user: str, followup: str) -> str:
    prev = prev_user.strip()
    fol = followup.strip()
    if not prev or not fol:
        return fol

    # Case 1: "y X?" -> keep previous environment/scope (e.g., "en linux")
    m_follow = re.match(r"(?i)^y\s+(.+?)[\?!.]?$", fol)
    m_prev_install = re.match(r"(?i)^como\s+instal[oa]\s+.+?(\s+en\s+.+?)?[\?!.]?$", prev)
    if m_follow and m_prev_install:
        target = m_follow.group(1).strip()
        scope = (m_prev_install.group(1) or "").strip()
        if scope:
            return f"como instalo {target} {scope}?"
        return f"como instalo {target}?"

    # Case 2: generic short follow-up -> embed previous question explicitly but as one direct ask.
    return f"Con base en esta pregunta previa: {prev}\nResponde ahora a esta nueva pregunta concreta: {fol}"


def _last_turn_pair(history: list[dict[str, Any]], current_user_message: str) -> tuple[str, str]:
    if not history:
        return "", ""

    prev_user = ""
    prev_assistant = ""
    current_norm = current_user_message.strip()

    # Walk backwards and extract the previous assistant and previous user before current message.
    seen_current_user = False
    for item in reversed(history):
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if not content:
            continue

        if role == "assistant" and content.startswith("Hola. Envia un ticket."):
            continue

        if role == "user" and not seen_current_user:
            if content == current_norm:
                seen_current_user = True
                continue
            # If history does not contain current message verbatim, treat this as previous user anyway.
            seen_current_user = True

        if seen_current_user:
            if not prev_assistant and role == "assistant":
                prev_assistant = content
                continue
            if not prev_user and role == "user":
                prev_user = content
                if prev_assistant:
                    break

    return prev_user, prev_assistant


def _prompt_preview(prompt: str, max_len: int = 600) -> str:
    compact = " ".join(prompt.split())
    if len(compact) <= max_len:
        return compact
    return compact[:max_len].rstrip() + "..."


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


def _normalize_session_id(raw_session_id: Any) -> str:
    session_id = str(raw_session_id or "").strip()
    return session_id or "default-session"


def _mode_label(mode: str) -> str:
    labels = {
        SESSION_MODE_TRIAGE: "Triage inicial",
        SESSION_MODE_CHAT: "Chat generico",
        SESSION_MODE_RESOLVED: "Resuelto por referencia",
    }
    return labels.get(mode, mode)


async def _send_mode_update(websocket, request_id: str, session_id: str, mode: str):
    await websocket.send(
        json.dumps(
            {
                "type": "mode_update",
                "request_id": request_id,
                "session_id": session_id,
                "mode": mode,
                "label": _mode_label(mode),
            }
        )
    )


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
    return ""


def _support_lookup_ticket(ticket_text: str) -> tuple[dict[str, Any] | None, str | None]:
    if not SUPPORT_MCP_URL or not SUPPORT_MCP_TOKEN:
        return None, "SUPPORT_MCP_URL o SUPPORT_MCP_TOKEN no configurados."

    rpc_payload = {
        "jsonrpc": "2.0",
        "id": "local-agent-lookup",
        "method": "tools/call",
        "params": {
            "name": "support_lookup_ticket",
            "arguments": {"ticket_text": ticket_text, "k": 3},
        },
    }
    raw = json.dumps(rpc_payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        SUPPORT_MCP_URL,
        data=raw,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SUPPORT_MCP_TOKEN}",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, f"Lookup MCP falló: {exc}"

    if isinstance(body, dict) and body.get("error"):
        message = body["error"].get("message", "error desconocido")
        return None, f"MCP RPC error: {message}"

    result = body.get("result", {}) if isinstance(body, dict) else {}
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured, None

    content = result.get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    parsed = json.loads(str(item.get("text", "")))
                    if isinstance(parsed, dict):
                        return parsed, None
                except json.JSONDecodeError:
                    continue
    return None, "Lookup MCP no devolvió structuredContent."


def _build_resolved_answer(lookup_result: dict[str, Any]) -> str:
    matches = lookup_result.get("matches", [])
    if not isinstance(matches, list) or not matches:
        return "Se encontró una resolución previa, pero no hay detalles de referencia."

    first = matches[0] if isinstance(matches[0], dict) else {}
    ticket_id = str(first.get("ticket_id") or "").strip()
    problem_title = str(first.get("problem_title") or "").strip()
    source = str(first.get("source", "unknown"))
    solution_steps = first.get("solution_steps", [])

    lines = [
        "Se ha encontrado una incidencia similar en la base de conocimiento.",
        (
            f"Referencia principal: {ticket_id} ({source})"
            if ticket_id
            else f"Referencia principal: {source}"
        ),
    ]
    if problem_title:
        lines.append(f"Caso original: {problem_title}")

    if isinstance(solution_steps, list) and solution_steps:
        lines.append("")
        lines.append("Solución aplicada anteriormente:")
        for item in solution_steps:
            step = str(item).strip()
            if step:
                lines.append(step)
    else:
        snippet = str(first.get("snippet", "")).strip()
        if snippet:
            lines.append("")
            lines.append("Fragmento relevante:")
            lines.append(snippet)
    return "\n".join(lines)


def _extract_references(lookup_result: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    matches = lookup_result.get("matches", [])
    if not isinstance(matches, list):
        return refs
    for item in matches[:3]:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                "source": str(item.get("source", "unknown")),
                "ticket_id": item.get("ticket_id"),
                "snippet": str(item.get("snippet", "")),
            }
        )
    return refs


async def _run_codex_and_stream(
    websocket,
    request_id: str,
    prompt: str,
    input_text_for_usage: str | None = None,
):
    await _trace(websocket, request_id, f"[prompt_preview] {_prompt_preview(prompt)}", force=True)

    codex_bin = shutil.which("codex")
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

    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "resolved": {"type": "boolean"},
            "references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "snippet": {"type": "string"},
                    },
                    "required": ["source", "snippet"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["answer", "resolved", "references"],
        "additionalProperties": False,
    }

    schema_path = None
    output_path = None
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as schema_file:
        json.dump(schema, schema_file, ensure_ascii=False)
        schema_path = schema_file.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as output_file:
        output_path = output_file.name

    cmd = [
        codex_bin,
        "exec",
        "--ephemeral",
        "--json",
        "--output-schema",
        schema_path,
        "-o",
        output_path,
        prompt,
    ]
    await _trace(
        websocket,
        request_id,
        f"[codex_exec_cmd] {' '.join(cmd[:6])} ... -o {output_path}",
        force=True,
    )
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    accumulated = ""
    streamed_events = 0

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

            lowered = raw.lower()
            if "support_lookup_ticket" in lowered or "mcp" in lowered:
                await _trace(websocket, request_id, raw[:1500], force=True)

        return_code = await process.wait()
        await _trace(
            websocket,
            request_id,
            f"[codex_exec_exit] code={return_code} streamed_events={streamed_events}",
            force=True,
        )

        stderr_text = (await process.stderr.read()).decode("utf-8", errors="replace")
        if stderr_text.strip():
            await _trace(
                websocket,
                request_id,
                f"[codex_stderr] {stderr_text[:1500]}",
            )

        if return_code != 0:
            await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "request_id": request_id,
                        "message": f"codex exec fallo con codigo {return_code}: {stderr_text[:2000]}",
                    }
                )
            )
            return

        references = []
        final_answer = accumulated.strip()
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                parsed = json.load(f)
                if isinstance(parsed, dict):
                    final_answer = str(parsed.get("answer", final_answer)).strip()
                    references = parsed.get("references", []) or []
                    await _trace(
                        websocket,
                        request_id,
                        (
                            f"[codex_output_json] has_answer={bool(parsed.get('answer'))} "
                            f"resolved={parsed.get('resolved')} refs={len(references)}"
                        ),
                        force=True,
                    )
                    if final_answer:
                        await _trace(
                            websocket,
                            request_id,
                            f"[codex_answer_preview] {_prompt_preview(final_answer)}",
                            force=True,
                        )
                else:
                    await _trace(websocket, request_id, "[codex_output_json] parsed_non_dict", force=True)
        except Exception:
            await _trace(websocket, request_id, "[codex_output_json] read_or_parse_failed", force=True)

        usage = _build_token_usage(input_text_for_usage or prompt, final_answer)

        await websocket.send(
            json.dumps(
                {
                    "type": "final_answer",
                    "request_id": request_id,
                    "answer": final_answer,
                    "references": references,
                    "token_usage": usage,
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
        for path in [schema_path, output_path]:
            if not path:
                continue
            try:
                os.remove(path)
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

            request_id = message.get("request_id", "")
            prompt = message.get("prompt", "")
            history = message.get("history", [])
            session_id = _normalize_session_id(message.get("session_id"))
            await _send_mode_update(
                websocket,
                request_id=request_id,
                session_id=session_id,
                mode=SESSION_MODE_TRIAGE,
            )

            lookup_result, lookup_error = await asyncio.to_thread(_support_lookup_ticket, prompt)
            if lookup_error:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "tool_trace",
                            "request_id": request_id,
                            "detail": lookup_error,
                        }
                    )
                )

            if isinstance(lookup_result, dict):
                resolved = bool(lookup_result.get("resolved"))
                await websocket.send(
                    json.dumps(
                        {
                            "type": "tool_trace",
                            "request_id": request_id,
                            "detail": f"support_lookup_ticket resolved={resolved}",
                        }
                    )
                )
                if resolved:
                    resolved_answer = _build_resolved_answer(lookup_result)
                    usage = _build_token_usage(prompt, resolved_answer)
                    await _send_mode_update(
                        websocket,
                        request_id=request_id,
                        session_id=session_id,
                        mode=SESSION_MODE_RESOLVED,
                    )
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "final_answer",
                                "request_id": request_id,
                                "answer": resolved_answer,
                                "references": _extract_references(lookup_result),
                                "token_usage": usage,
                            }
                        )
                    )
                    continue

            await _send_mode_update(
                websocket,
                request_id=request_id,
                session_id=session_id,
                mode=SESSION_MODE_CHAT,
            )
            built_prompt = _build_chat_prompt(prompt, history)
            await _run_codex_and_stream(
                websocket,
                request_id=request_id,
                prompt=built_prompt,
                input_text_for_usage=prompt,
            )


async def _ensure_mcp_server_config():
    codex_bin = shutil.which("codex")
    if not codex_bin or not SUPPORT_MCP_URL:
        return

    if SUPPORT_MCP_TOKEN:
        os.environ["SUPPORT_MCP_TOKEN"] = SUPPORT_MCP_TOKEN

    check = await asyncio.create_subprocess_exec(
        codex_bin,
        "mcp",
        "get",
        "support-rag",
        "--json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    check_code = await check.wait()
    if check_code == 0:
        return

    add = await asyncio.create_subprocess_exec(
        codex_bin,
        "mcp",
        "add",
        "support-rag",
        "--url",
        SUPPORT_MCP_URL,
        "--bearer-token-env-var",
        "SUPPORT_MCP_TOKEN",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await add.wait()


async def main():
    await _ensure_mcp_server_config()
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
