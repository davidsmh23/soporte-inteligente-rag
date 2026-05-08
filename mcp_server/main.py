import json
import os
from typing import Any, Dict, List

import httpx
from fastapi import Body, FastAPI, Header, HTTPException, Response

app = FastAPI(
    title="Support MCP Server",
    version="1.0.0",
    description="MCP server exposing support triage tools over streamable HTTP-style JSON-RPC.",
)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")
MCP_BEARER_TOKEN = os.environ.get("MCP_BEARER_TOKEN", "")


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "support_lookup_ticket",
        "description": (
            "Lookup if a ticket was solved before using ChromaDB semantic search. "
            "Returns resolved flag, route_hint, and matching knowledge snippets with references."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_text": {"type": "string"},
                "k": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
                "threshold": {"type": "number", "minimum": 0},
            },
            "required": ["ticket_text"],
        },
    },
    {
        "name": "support_index_knowledge",
        "description": "Index markdown knowledge base into ChromaDB.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _validate_bearer(authorization: str | None) -> None:
    if not MCP_BEARER_TOKEN:
        raise HTTPException(status_code=500, detail="MCP_BEARER_TOKEN is not configured in server.")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    provided = authorization.split(" ", 1)[1].strip()
    if provided != MCP_BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")


def _rpc_result(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/mcp")
async def mcp_get_probe(authorization: str | None = Header(default=None)):
    _validate_bearer(authorization)
    return {"status": "ok", "message": "Use POST /mcp for JSON-RPC requests."}


@app.post("/mcp")
async def mcp_endpoint(payload: Any = Body(...), authorization: str | None = Header(default=None)):
    _validate_bearer(authorization)

    if isinstance(payload, list):
        responses = []
        for item in payload:
            response = await _handle_rpc_item(item)
            if response is not None:
                responses.append(response)
        if not responses:
            return Response(status_code=202)
        return responses

    response = await _handle_rpc_item(payload)
    if response is None:
        return Response(status_code=202)
    return response


async def _handle_rpc_item(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    method = payload.get("method")
    request_id = payload.get("id")
    params = payload.get("params", {}) or {}

    # JSON-RPC notifications can omit id. We acknowledge with HTTP 202.
    if request_id is None and method in {"notifications/initialized", "initialized"}:
        return None

    try:
        if method == "ping":
            return _rpc_result(request_id, {})

        if method == "initialize":
            return _rpc_result(
                request_id,
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "support-mcp-server", "version": "1.0.0"},
                },
            )

        if method == "tools/list":
            return _rpc_result(request_id, {"tools": TOOLS})

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {}) or {}
            result = await _handle_tool_call(tool_name, arguments)
            return _rpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "structuredContent": result,
                    "isError": False,
                },
            )

        return _rpc_error(request_id, -32601, f"Method not found: {method}")
    except HTTPException as exc:
        return _rpc_error(request_id, -32001, str(exc.detail))
    except Exception as exc:
        return _rpc_error(request_id, -32603, f"Internal error: {exc}")


async def _handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "support_lookup_ticket":
        return await _lookup_ticket(arguments)
    if tool_name == "support_index_knowledge":
        return await _index_knowledge()
    raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")


async def _lookup_ticket(arguments: Dict[str, Any]) -> Dict[str, Any]:
    ticket_text = arguments.get("ticket_text")
    if not ticket_text:
        raise HTTPException(status_code=400, detail="support_lookup_ticket requires 'ticket_text'.")

    payload = {
        "ticket_text": ticket_text,
        "k": int(arguments.get("k", 3)),
        "threshold": arguments.get("threshold"),
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{BACKEND_URL}/api/v1/rag/lookup", json=payload)
        response.raise_for_status()
        return response.json()


async def _index_knowledge() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{BACKEND_URL}/api/v1/knowledge/index")
        response.raise_for_status()
        return response.json()
