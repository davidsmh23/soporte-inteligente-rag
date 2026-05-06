# Flujo MCP-first: Streamlit (servidor) <-> Codex CLI (cliente)

## Componentes

- `backend` (FastAPI): indexacion y lookup semantico en ChromaDB.
- `mcp-server` (FastAPI JSON-RPC): tools MCP remotas:
  - `support_lookup_ticket`
  - `support_index_knowledge`
- `session-gateway` (FastAPI + WebSocket): puente entre Streamlit y agentes Codex locales.
- `frontend` (Streamlit): UI de chat + estado de agente + referencias.
- `local_agent` (cliente): mantiene conexion saliente al gateway y ejecuta `codex exec`.

## Variables clave (servidor)

- `EMBEDDING_API_KEY` o `GOOGLE_API_KEY`
- `MCP_BEARER_TOKEN`
- `SESSION_USER_TOKENS` (ej. `alice:token-a,bob:token-b`)
- `DEFAULT_USER_ID`
- `DEFAULT_USER_TOKEN`

## Levantar servidor

```bash
docker compose up --build
```

Servicios:

- Streamlit: `http://<server>:8501`
- Backend: `http://<server>:8502`
- MCP: `http://<server>:8100/mcp`
- Session gateway: `http://<server>:9000`

## Arrancar agente local (cliente)

En el equipo del usuario (donde corre `codex`):

```bash
cd local_agent
python -m venv .venv
. .venv/bin/activate  # en Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Variables minimas:

```bash
export SESSION_GATEWAY_WS_URL="ws://<server>:9000/ws/agent"
export SESSION_USER_ID="alice"
export SESSION_USER_TOKEN="token-a"
export SUPPORT_MCP_URL="http://<server>:8100/mcp"
export SUPPORT_MCP_TOKEN="<MCP_BEARER_TOKEN>"
python main.py
```

## Flujo funcional

1. Usuario envia ticket desde Streamlit.
2. Streamlit llama `session-gateway` (`/api/v1/session/prompt`) con streaming SSE.
3. Gateway reenvia prompt al `local_agent` por WebSocket.
4. `local_agent` ejecuta `codex exec`:
   - primero usa `support_lookup_ticket`
   - si `resolved=true`: responde con solucion + referencias
   - si `resolved=false`: fallback temporal a chat conversacional
   - en chat conversacional corre con `shell_tool` deshabilitado, `cwd` aislado y sin inspeccion del repo local
5. Streamlit muestra respuesta incremental y bloque de referencias.
