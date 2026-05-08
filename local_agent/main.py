import asyncio
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

import websockets

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None

SESSION_GATEWAY_WS_URL = os.environ.get(
    "SESSION_GATEWAY_WS_URL", "ws://localhost:9000/ws/agent"
)
SESSION_USER_ID = os.environ.get("SESSION_USER_ID", "demo")
SESSION_USER_TOKEN = os.environ.get("SESSION_USER_TOKEN", "demo-token")
CODEX_EXEC_TIMEOUT_SEC = int(os.environ.get("CODEX_EXEC_TIMEOUT_SEC", "300"))
DIAGNOSTIC_VERBOSE = os.environ.get("DIAGNOSTIC_VERBOSE", "1").strip() not in {
    "0",
    "false",
    "False",
}
SUPPORT_MCP_URL = os.environ.get("SUPPORT_MCP_URL", "http://localhost:8100/mcp").strip()
SUPPORT_MCP_TIMEOUT_SEC = int(os.environ.get("SUPPORT_MCP_TIMEOUT_SEC", "45"))
SUPPORT_LOOKUP_K = int(os.environ.get("SUPPORT_LOOKUP_K", "3"))
_raw_threshold = os.environ.get("SUPPORT_LOOKUP_THRESHOLD", "").strip()
SUPPORT_LOOKUP_THRESHOLD = float(_raw_threshold) if _raw_threshold else None
CODEX_EXEC_CWD = os.environ.get("CODEX_EXEC_CWD", "").strip()
DISABLE_LOCAL_INSPECTION = os.environ.get(
    "DISABLE_LOCAL_INSPECTION", "1"
).strip().lower() not in {"0", "false", "no"}

SESSION_MODE_CHAT = "chat_generico"
SESSION_MODE_TRIAGE = "triage_inicial"
SESSION_MODE_RESOLVED = "resuelto_por_referencia"
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
UUID_INLINE_RE = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)
CONVERSATION_MODE: dict[str, str] = {}
THREAD_EVENT_TYPES = {"thread.started", "thread_name_updated", "thread.updated"}
SESSION_UUID_KEYS = ("thread_id", "session_id", "id")
NULLISH_SESSION_VALUES = {"none", "null", "undefined"}
CODEX_BIN_CANDIDATES = ("codex.cmd", "codex.exe", "codex")
MODE_LABELS = {
    SESSION_MODE_TRIAGE: "Triage inicial",
    SESSION_MODE_CHAT: "Chat generico",
    SESSION_MODE_RESOLVED: "Resuelto por referencia",
}
LOCAL_INSPECTION_GUARD = (
    "Reglas obligatorias de esta sesion:\n"
    "- No uses herramientas locales ni shell.\n"
    "- No inspecciones archivos del entorno ni del repositorio.\n"
    "- No afirmes que revisaste codigo, docker-compose, logs o carpetas locales.\n"
    "- Responde solo con la informacion escrita por el usuario y tus conocimientos.\n"
    "- Si faltan datos, pide al usuario comandos/logs concretos para continuar.\n\n"
    "Consulta del usuario:\n"
)


def _is_local_host(hostname: str | None) -> bool:
    return str(hostname or "").strip().lower() in {"localhost", "127.0.0.1", "::1"}


def _build_support_mcp_urls() -> list[str]:
    configured = SUPPORT_MCP_URL.strip()
    urls: list[str] = []
    if configured:
        urls.append(configured)

    ws = urllib_parse.urlparse(SESSION_GATEWAY_WS_URL.strip())
    ws_host = ws.hostname
    if not ws_host:
        return urls

    configured_host = None
    configured_port = 8100
    configured_path = "/mcp"
    if configured:
        parsed = urllib_parse.urlparse(configured)
        configured_host = parsed.hostname
        configured_port = parsed.port or configured_port
        if parsed.path:
            configured_path = parsed.path

    should_add_ws_fallback = not configured or (
        _is_local_host(configured_host) and not _is_local_host(ws_host)
    )
    if not should_add_ws_fallback:
        return urls

    fallback_scheme = "https" if ws.scheme == "wss" else "http"
    fallback_netloc = f"{ws_host}:{configured_port}"
    fallback_url = urllib_parse.urlunparse(
        (fallback_scheme, fallback_netloc, configured_path, "", "", "")
    )
    if fallback_url not in urls:
        urls.append(fallback_url)
    return urls


async def _send_json(websocket, payload: dict[str, Any]) -> None:
    await websocket.send(json.dumps(payload))


async def _send_error(
    websocket, request_id: str, message: str, *, code: str | None = None
) -> None:
    payload: dict[str, Any] = {
        "type": "error",
        "request_id": request_id,
        "message": message,
    }
    if code:
        payload["code"] = code
    await _send_json(websocket, payload)


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
    method = (
        input_method
        if input_method == output_method
        else f"{input_method}+{output_method}"
    )
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
        for key in SESSION_UUID_KEYS:
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
        if payload_type in THREAD_EVENT_TYPES:
            return _find_uuid(payload)

    if event_type in THREAD_EVENT_TYPES:
        return _find_uuid(event)

    return _find_uuid(event)


def _extract_uuid_from_text(text: str) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    # Avoid binding to arbitrary UUIDs from diagnostics/errors; only accept
    # explicit session continuation hints.
    if (
        "codex resume" not in lowered
        and "thread.started" not in lowered
        and "thread_id" not in lowered
    ):
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
    if lowered in NULLISH_SESSION_VALUES:
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
    await _send_json(
        websocket,
        {
            "type": "tool_trace",
            "request_id": request_id,
            "detail": detail,
        },
    )


def _mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


async def _send_mode_update(
    websocket, request_id: str, conversation_id: str, mode: str
):
    await _send_json(
        websocket,
        {
            "type": "mode_update",
            "request_id": request_id,
            "conversation_id": conversation_id,
            "mode": mode,
            "label": _mode_label(mode),
        },
    )


def _resolve_codex_bin() -> str | None:
    explicit = os.environ.get("CODEX_BIN", "").strip()
    if explicit and Path(explicit).exists():
        return explicit

    for candidate in CODEX_BIN_CANDIDATES:
        path = shutil.which(candidate)
        if path:
            return path
    return None


def _resolve_codex_exec_cwd() -> Path:
    if CODEX_EXEC_CWD:
        root = Path(CODEX_EXEC_CWD).expanduser()
    else:
        root = Path(tempfile.gettempdir()) / "support-agent-codex-workdir"
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"No se pudo preparar CODEX_EXEC_CWD '{root}': {exc}"
        ) from exc
    return root


def _build_effective_prompt(prompt_text: str) -> str:
    if not DISABLE_LOCAL_INSPECTION:
        return prompt_text
    return f"{LOCAL_INSPECTION_GUARD}{prompt_text}"


def _load_value_from_root_env(key: str) -> str | None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    try:
        for raw_line in env_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() != key:
                continue
            return value.strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def _build_codex_cmd(
    codex_bin: str, output_path: str, known_session: str | None, exec_cwd: Path
) -> list[str]:
    # Hard security boundary: no file edits and no approval escalation.
    safe_exec_flags = [
        "-c",
        'sandbox_mode="read-only"',
        "-c",
        'approval_policy="never"',
    ]
    base = [
        codex_bin,
        "-C",
        str(exec_cwd),
        "--disable",
        "shell_tool",
        "exec",
        "--skip-git-repo-check",
        "--ignore-rules",
    ]
    if known_session:
        return [
            *base,
            "resume",
            *safe_exec_flags,
            "--json",
            "-o",
            output_path,
            known_session,
            "-",
        ]
    return [
        *base,
        *safe_exec_flags,
        "--json",
        "-o",
        output_path,
        "-",
    ]


async def _send_conversation_bound(
    websocket,
    request_id: str,
    conversation_id: str,
    codex_session_id: str,
) -> None:
    await _send_json(
        websocket,
        {
            "type": "conversation_bound",
            "request_id": request_id,
            "conversation_id": conversation_id,
            "codex_session_id": codex_session_id,
        },
    )


def _build_resume_unavailable_payload(
    request_id: str, return_code: int, stderr_text: str
) -> dict[str, Any]:
    return {
        "type": "error",
        "request_id": request_id,
        "message": f"codex exec fallo con codigo {return_code}: {stderr_text[:2000]}",
    }


def _is_resume_error(
    known_session: str | None, stderr_text: str, accumulated: str
) -> bool:
    lowered = f"{stderr_text} {accumulated}".lower()
    return bool(known_session) and (
        "resume" in lowered
        and ("not found" in lowered or "no session" in lowered)
        or "unknown session" in lowered
        or "invalid session" in lowered
    )


async def _send_final_answer(
    websocket,
    request_id: str,
    answer: str,
    references: list[dict[str, Any]],
    token_usage: dict[str, Any],
    codex_session_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "final_answer",
        "request_id": request_id,
        "answer": answer,
        "references": references,
        "token_usage": token_usage,
    }
    if codex_session_id is not None:
        payload["codex_session_id"] = codex_session_id
    await _send_json(websocket, payload)


def _resolve_support_mcp_token() -> str:
    token = os.environ.get("SUPPORT_MCP_TOKEN", "").strip()
    if token:
        return token
    fallback = _load_value_from_root_env("MCP_BEARER_TOKEN")
    return (fallback or "").strip()


def _sync_lookup_ticket(ticket_text: str) -> tuple[dict[str, Any], str]:
    token = _resolve_support_mcp_token()
    urls = _build_support_mcp_urls()
    if not urls:
        raise RuntimeError("SUPPORT_MCP_URL vacia.")
    if not token:
        raise RuntimeError("SUPPORT_MCP_TOKEN/MCP_BEARER_TOKEN no disponible.")

    arguments: dict[str, Any] = {
        "ticket_text": ticket_text,
        "k": SUPPORT_LOOKUP_K,
    }
    if SUPPORT_LOOKUP_THRESHOLD is not None:
        arguments["threshold"] = SUPPORT_LOOKUP_THRESHOLD

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "support_lookup_ticket",
            "arguments": arguments,
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    failures: list[str] = []
    for url in urls:
        req = urllib_request.Request(
            url=url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=SUPPORT_MCP_TIMEOUT_SEC) as resp:
                response_text = resp.read().decode("utf-8", errors="replace")
        except urllib_error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            failures.append(f"{url} -> HTTP {exc.code}: {error_body[:200]}")
            continue
        except urllib_error.URLError as exc:
            failures.append(f"{url} -> conexion fallida: {exc}")
            continue

        try:
            rpc = json.loads(response_text)
        except json.JSONDecodeError as exc:
            failures.append(f"{url} -> respuesta no JSON: {exc}")
            continue
        if not isinstance(rpc, dict):
            failures.append(f"{url} -> respuesta MCP invalida (no-objeto).")
            continue
        if isinstance(rpc.get("error"), dict):
            rpc_error = rpc["error"]
            failures.append(
                f"{url} -> RPC {rpc_error.get('code')}: {rpc_error.get('message')}"
            )
            continue

        result = rpc.get("result", {})
        structured = (
            result.get("structuredContent") if isinstance(result, dict) else None
        )
        if isinstance(structured, dict):
            return structured, url

        content = result.get("content") if isinstance(result, dict) else None
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and isinstance(first.get("text"), str):
                try:
                    parsed = json.loads(first["text"])
                except json.JSONDecodeError as exc:
                    failures.append(f"{url} -> content[0].text invalido: {exc}")
                    continue
                if isinstance(parsed, dict):
                    return parsed, url
        failures.append(f"{url} -> respuesta MCP sin structuredContent util.")

    detail = " | ".join(failures[-3:]) if failures else "sin detalle"
    raise RuntimeError(f"lookup sin exito en {len(urls)} endpoint(s): {detail}")


async def _drain_stderr(stream, max_chars: int = 20000) -> str:
    chunks: list[str] = []
    total = 0
    while True:
        block = await stream.read(4096)
        if not block:
            break
        text = block.decode("utf-8", errors="replace")
        chunks.append(text)
        total += len(text)
        if total > max_chars:
            overflow = total - max_chars
            while chunks and overflow > 0:
                head = chunks[0]
                if len(head) <= overflow:
                    overflow -= len(head)
                    chunks.pop(0)
                else:
                    chunks[0] = head[overflow:]
                    overflow = 0
            total = max_chars
    return "".join(chunks)


def _build_triage_references(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for match in matches:
        if not isinstance(match, dict):
            continue
        refs.append(
            {
                "source": str(match.get("source") or "unknown"),
                "ticket_id": match.get("ticket_id"),
                "snippet": str(match.get("snippet") or ""),
                "problem_title": match.get("problem_title"),
                "solution_steps": (
                    match.get("solution_steps")
                    if isinstance(match.get("solution_steps"), list)
                    else []
                ),
                "score": match.get("score"),
            }
        )
    return refs


def _build_triage_answer(match: dict[str, Any]) -> str:
    ticket_id = str(match.get("ticket_id") or "").strip()
    source = str(match.get("source") or "unknown_source").strip()
    problem_title = str(match.get("problem_title") or "").strip()
    snippet = str(match.get("snippet") or "").strip()
    steps_raw = match.get("solution_steps")
    steps = steps_raw if isinstance(steps_raw, list) else []
    score = match.get("score")

    lines: list[str] = [
        "He encontrado una incidencia similar en la base de conocimiento.",
        f"Referencia: {ticket_id or '(sin id_ticket)'} ({source})",
    ]
    if problem_title:
        lines.append(f"Problema relacionado: {problem_title}")
    if isinstance(score, (int, float)):
        lines.append(f"Score de similitud: {float(score):.4f}")

    if steps:
        lines.append("")
        lines.append("Pasos de solucion registrada:")
        for idx, step in enumerate(steps, start=1):
            clean = str(step).strip()
            if clean:
                lines.append(f"{idx}. {clean}")
    elif snippet:
        lines.append("")
        lines.append("Fragmento relevante:")
        lines.append(snippet)

    return "\n".join(lines)


async def _run_codex_and_stream(
    websocket,
    request_id: str,
    conversation_id: str,
    prompt: str,
    codex_session_id: str | None,
):
    codex_bin = _resolve_codex_bin()
    if not codex_bin:
        await _send_error(
            websocket,
            request_id,
            "No se encontro el binario 'codex' en el cliente local.",
        )
        return

    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        await _send_error(websocket, request_id, "Prompt vacio.")
        return
    effective_prompt = _build_effective_prompt(prompt_text)

    known_session = _normalize_codex_session_id(codex_session_id)
    try:
        exec_cwd = _resolve_codex_exec_cwd()
    except RuntimeError as exc:
        await _send_error(websocket, request_id, str(exc))
        return
    output_path = None
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as output_file:
        output_path = output_file.name

    before_sessions = _read_recent_session_ids() if not known_session else []
    cmd = _build_codex_cmd(codex_bin, output_path, known_session, exec_cwd)

    await _trace(
        websocket,
        request_id,
        f"[prompt_preview] {_prompt_preview(prompt_text)}",
        force=True,
    )
    await _trace(websocket, request_id, f"[exec_cwd] {exec_cwd}", force=True)
    await _trace(
        websocket, request_id, f"[codex_cmd] {' '.join(cmd[:7])} ...", force=True
    )

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    if process.stdin:
        process.stdin.write(effective_prompt.encode("utf-8"))
        await process.stdin.drain()
        process.stdin.close()

    accumulated = ""
    streamed_events = 0
    detected_thread_id = known_session
    stderr_task = (
        asyncio.create_task(_drain_stderr(process.stderr)) if process.stderr else None
    )

    try:
        while True:
            line = await asyncio.wait_for(
                process.stdout.readline(), timeout=CODEX_EXEC_TIMEOUT_SEC
            )
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
                    await _send_conversation_bound(
                        websocket,
                        request_id=request_id,
                        conversation_id=conversation_id,
                        codex_session_id=detected_thread_id,
                    )

            event_text = _extract_text(event)
            if event_text:
                accumulated += event_text + "\n"
                streamed_events += 1
                await _send_json(
                    websocket,
                    {
                        "type": "token_delta",
                        "request_id": request_id,
                        "delta": event_text + "\n",
                    },
                )

        return_code = await process.wait()
        stderr_text = await stderr_task if stderr_task else ""
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
                await _send_conversation_bound(
                    websocket,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    codex_session_id=detected_thread_id,
                )

        if return_code != 0:
            payload = _build_resume_unavailable_payload(
                request_id, return_code, stderr_text
            )
            if _is_resume_error(known_session, stderr_text, accumulated):
                payload["code"] = "agent_unavailable"
                payload["message"] = (
                    "La sesion de Codex no esta disponible en este agente local. "
                    "Conecta el agente original para continuar esta conversacion."
                )
            await _send_json(websocket, payload)
            return

        final_answer = accumulated.strip()
        try:
            if output_path and os.path.exists(output_path):
                output_text = (
                    Path(output_path)
                    .read_text(encoding="utf-8", errors="replace")
                    .strip()
                )
                if output_text:
                    final_answer = output_text
        except OSError:
            pass
        if not final_answer:
            final_answer = "No se genero contenido en esta ejecucion de Codex."

        usage = _build_token_usage(prompt_text, final_answer)
        await _send_final_answer(
            websocket,
            request_id=request_id,
            answer=final_answer,
            references=[],
            token_usage=usage,
            codex_session_id=detected_thread_id,
        )
    except asyncio.TimeoutError:
        process.kill()
        if stderr_task:
            try:
                await asyncio.wait_for(stderr_task, timeout=2)
            except Exception:
                stderr_task.cancel()
        await _send_error(websocket, request_id, "Timeout en ejecucion de codex exec.")
    finally:
        if stderr_task and not stderr_task.done():
            stderr_task.cancel()
        if output_path:
            try:
                os.remove(output_path)
            except OSError:
                pass


async def _run_initial_triage(
    websocket,
    request_id: str,
    conversation_id: str,
    prompt_text: str,
) -> tuple[bool, str, list[dict[str, Any]]]:
    await _trace(
        websocket,
        request_id,
        f"[triage_lookup] urls={_build_support_mcp_urls()} k={SUPPORT_LOOKUP_K} threshold={SUPPORT_LOOKUP_THRESHOLD}",
    )
    lookup, used_url = await asyncio.to_thread(_sync_lookup_ticket, prompt_text)
    resolved = bool(lookup.get("resolved"))
    matches_raw = lookup.get("matches")
    matches = matches_raw if isinstance(matches_raw, list) else []
    references = _build_triage_references(matches)
    top_ref = references[0] if references else None

    await _trace(
        websocket,
        request_id,
        (
            f"[triage_lookup] url={used_url} resolved={resolved} "
            f"route_hint={lookup.get('route_hint')} "
            f"top_ticket={top_ref.get('ticket_id') if isinstance(top_ref, dict) else None}"
        ),
    )
    if not resolved or not matches or not isinstance(matches[0], dict):
        return False, "", references

    answer = _build_triage_answer(matches[0])
    usage = _build_token_usage(prompt_text, answer)
    await _send_mode_update(
        websocket,
        request_id=request_id,
        conversation_id=conversation_id,
        mode=SESSION_MODE_RESOLVED,
    )
    await _send_final_answer(
        websocket,
        request_id=request_id,
        answer=answer,
        references=references,
        token_usage=usage,
    )
    return True, answer, references


async def _handle_conversation_mode(
    websocket,
    request_id: str,
    conversation_id: str,
    prompt: str,
) -> bool:
    current_mode = CONVERSATION_MODE.get(conversation_id)
    if current_mode is None:
        CONVERSATION_MODE[conversation_id] = SESSION_MODE_TRIAGE
        await _send_mode_update(
            websocket,
            request_id=request_id,
            conversation_id=conversation_id,
            mode=SESSION_MODE_TRIAGE,
        )
        try:
            triage_resolved, _, _ = await _run_initial_triage(
                websocket,
                request_id=request_id,
                conversation_id=conversation_id,
                prompt_text=prompt,
            )
        except Exception as exc:
            await _trace(websocket, request_id, f"[triage_lookup_error] {exc}")
            triage_resolved = False

        if triage_resolved:
            CONVERSATION_MODE[conversation_id] = SESSION_MODE_RESOLVED
            return True

        CONVERSATION_MODE[conversation_id] = SESSION_MODE_CHAT
        await _send_mode_update(
            websocket,
            request_id=request_id,
            conversation_id=conversation_id,
            mode=SESSION_MODE_CHAT,
        )
        return False

    if current_mode != SESSION_MODE_CHAT:
        CONVERSATION_MODE[conversation_id] = SESSION_MODE_CHAT
        await _send_mode_update(
            websocket,
            request_id=request_id,
            conversation_id=conversation_id,
            mode=SESSION_MODE_CHAT,
        )
    return False


async def _run_once():
    ws_url = f"{SESSION_GATEWAY_WS_URL.rstrip('/')}/{SESSION_USER_ID}?token={SESSION_USER_TOKEN}"
    async with websockets.connect(
        ws_url, max_size=None, ping_interval=20, ping_timeout=20
    ) as websocket:
        while True:
            raw = await websocket.recv()
            message = json.loads(raw)
            if message.get("type") == "server_ping":
                continue
            if message.get("type") != "prompt":
                continue

            request_id = str(message.get("request_id", "")).strip()
            prompt = str(message.get("prompt", "")).strip()
            conversation_id = (
                str(message.get("conversation_id", "")).strip()
                or "default-conversation"
            )
            codex_session_id = _normalize_codex_session_id(
                message.get("codex_session_id")
            )
            if await _handle_conversation_mode(
                websocket,
                request_id=request_id,
                conversation_id=conversation_id,
                prompt=prompt,
            ):
                continue

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
