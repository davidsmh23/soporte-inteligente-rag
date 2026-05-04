# Asistente de Soporte Inteligente (V2)

Sistema de soporte tecnico con RAG sobre Obsidian + flujo conversacional con Codex CLI.

## Novedades

- Flujo RAG determinista (Top-1 + umbral).
- Si hay match:
  - respuesta con referencia explicita al ticket original (`id_ticket`)
  - nombre del `.md`
  - pasos completos de `# Solucion Exitosa`
- Si no hay match:
  - fallback automatico a chat conversacional con Codex.
- `local_agent` ejecuta siempre lookup MCP antes de `codex exec`.
- UI muestra trazas MCP/Codex y referencias por ticket.
- Corregido error MCP `422` en `POST /mcp` (parseo de body JSON-RPC).

## Arquitectura

Servicios:

- `frontend` (Streamlit)
- `backend` (FastAPI + RAG + Chroma lookup)
- `mcp-server` (tooling MCP via JSON-RPC)
- `session-gateway` (bridge Streamlit <-> local_agent)
- `chromadb` (vector DB)
- `local_agent` (proceso local del usuario con Codex CLI)

Flujo:

1. Streamlit envia prompt a `session-gateway`.
2. `session-gateway` lo enruta al `local_agent` por WebSocket.
3. `local_agent` llama `support_lookup_ticket` (MCP).
4. Si `resolved=true`, responde con solucion historica referenciada.
5. Si `resolved=false`, ejecuta `codex exec` conversacional.

## Puertos

- Frontend: `8501`
- Backend: `8502`
- MCP server: `8100`
- Session gateway: `9000`
- ChromaDB: `8033`

## Inicio rapido

```bash
git clone https://github.com/<tu-org>/<tu-repo>.git
cd <tu-repo>
cp .env.example .env
docker compose up -d --build
```

Abrir:

- `http://localhost:8501`

## Variables de entorno clave

Servidor (`.env`):

- `EMBEDDING_API_KEY`: clave para embeddings.
- `MCP_BEARER_TOKEN`: token de autenticacion MCP.
- `SESSION_USER_TOKENS`: mapa `user:token`.
- `DEFAULT_USER_ID`
- `DEFAULT_USER_TOKEN`

Cliente local (`local_agent`):

- `SESSION_GATEWAY_WS_URL` (ej: `ws://localhost:9000/ws/agent`)
- `SESSION_USER_ID`
- `SESSION_USER_TOKEN`
- `SUPPORT_MCP_URL` (ej: `http://localhost:8100/mcp`)
- `SUPPORT_MCP_TOKEN`

Nota: si `SUPPORT_MCP_TOKEN` no esta definido, `local_agent` intenta cargar `MCP_BEARER_TOKEN` desde `../.env`.

## Verificacion rapida

```bash
curl http://localhost:8502/health
curl http://localhost:8100/health
curl http://localhost:9000/health
```

En UI deben verse:

- `Backend conectado`
- `Agente local: Conectado y libre`

## Endpoints utiles

- `POST /api/v1/knowledge/index` (backend)
- `POST /api/v1/rag/lookup` (backend)
- `POST /mcp` (mcp-server, JSON-RPC)
- `POST /api/v1/session/prompt` (session-gateway)
- `GET /api/v1/agents/{user_id}/status` (session-gateway)

## Troubleshooting

### Lookup MCP falla con `HTTP 422`

Recrear `mcp-server`:

```bash
docker compose up -d --build mcp-server
```

### `Invalid user token`

- Revisar `SESSION_USER_TOKENS` y token en UI/cliente.
- Confirmar cabecera `Authorization: Bearer <token>`.

### Backend no levanta

```bash
docker compose logs --tail 200 backend
```

### Agente local sin respuesta

- Reiniciar `local_agent`.
- Revisar bloque `Trazas MCP/Codex` en la UI.
- Validar estado:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:9000/api/v1/agents/demo/status
```
