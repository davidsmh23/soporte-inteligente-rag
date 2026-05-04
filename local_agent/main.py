import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

import websockets

SESSION_GATEWAY_WS_URL = os.environ.get("SESSION_GATEWAY_WS_URL", "ws://localhost:9000/ws/agent")
SESSION_USER_ID = os.environ.get("SESSION_USER_ID", "demo")
SESSION_USER_TOKEN = os.environ.get("SESSION_USER_TOKEN", "demo-token")
CODEX_EXEC_TIMEOUT_SEC = int(os.environ.get("CODEX_EXEC_TIMEOUT_SEC", "300"))
SUPPORT_MCP_URL = os.environ.get("SUPPORT_MCP_URL", "http://localhost:8100/mcp")
SUPPORT_MCP_TOKEN = os.environ.get("SUPPORT_MCP_TOKEN", "")


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


def _build_prompt(ticket_text: str, history: list[dict[str, Any]]) -> str:
    history_text = ""
    if history:
        lines = []
        for item in history[-10:]:
            role = item.get("role", "user")
            content = item.get("content", "")
            lines.append(f"{role}: {content}")
        history_text = "\n\nHistorial reciente:\n" + "\n".join(lines)

    return (
        "Eres un asistente de soporte tecnico.\n"
        "Regla obligatoria: primero llama a la tool MCP support_lookup_ticket con el ticket actual.\n"
        "Si resolved=true: responde con la solucion y lista referencias en formato archivo + fragmento.\n"
        "Si resolved=false: continua en modo chatbot conversacional de soporte tecnico.\n"
        "Responde en espanol.\n"
        "Tu salida FINAL debe ser JSON valido que cumpla el esquema indicado por --output-schema.\n\n"
        f"Ticket actual:\n{ticket_text}"
        f"{history_text}"
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


async def _run_codex_and_stream(websocket, request_id: str, prompt: str):
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
        "--json",
        "--output-schema",
        schema_path,
        "-o",
        output_path,
        prompt,
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    accumulated = ""

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
                await websocket.send(
                    json.dumps(
                        {
                            "type": "tool_trace",
                            "request_id": request_id,
                            "detail": raw[:1500],
                        }
                    )
                )

        return_code = await process.wait()
        if return_code != 0:
            stderr_text = (await process.stderr.read()).decode("utf-8", errors="replace")
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
        except Exception:
            pass

        await websocket.send(
            json.dumps(
                {
                    "type": "final_answer",
                    "request_id": request_id,
                    "answer": final_answer,
                    "references": references,
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
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "final_answer",
                                "request_id": request_id,
                                "answer": _build_resolved_answer(lookup_result),
                                "references": _extract_references(lookup_result),
                            }
                        )
                    )
                    continue

            built_prompt = _build_prompt(prompt, history)
            await _run_codex_and_stream(websocket, request_id=request_id, prompt=built_prompt)


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
