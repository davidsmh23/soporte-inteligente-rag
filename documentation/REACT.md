# Migracion de Frontend a React

## Alcance

Migrar `frontend/app.py` (Streamlit) a una SPA React sin cambiar contratos del backend, `session-gateway` ni `local_agent`.

## Estado real actual (codigo, no objetivo)

El frontend actual (`frontend/app.py`) no usa el chat HTTP directo de backend para conversar. El flujo real de chat pasa por `session-gateway` y SSE.

### Servicios actuales relevantes

- `backend`:
  - `GET /health`
  - `POST /api/v1/knowledge/index`
  - `POST /api/v1/chat/` (existe, pero no es el flujo principal de la UI actual)
- `session-gateway`:
  - `GET /api/v1/agents/{user_id}/status`
  - `POST /api/v1/conversations`
  - `GET /api/v1/conversations`
  - `GET /api/v1/conversations/{conversation_ref}`
  - `POST /api/v1/session/prompt` (stream SSE)
- `local_agent`:
  - Conecta por WebSocket a `session-gateway`
  - Emite eventos `mode_update`, `conversation_bound`, `token_delta`, `final_answer`, `tool_trace`, `error`

## Requisito de paridad funcional

La version React debe replicar estas capacidades del Streamlit actual:

1. Configuracion de sesion: `user_id` y `user_token`.
2. Estado backend y estado de agente local.
3. Indexacion de conocimiento (`/api/v1/knowledge/index`).
4. Lista de conversaciones persistidas.
5. Conversacion activa con `conversation_id` y `codex_session_id`.
6. Streaming incremental de respuesta (SSE).
7. Render de referencias y uso de tokens por respuesta.
8. Visualizacion de trazas (`tool_trace`) y cambios de modo (`mode_update`).

## Contratos API a respetar

## Headers

- Todas las llamadas a `session-gateway` requieren:
  - `Authorization: Bearer <user_token>`

## Conversaciones

- `POST /api/v1/conversations`
  - body: `{ "user_id": string, "title": string }`
- `GET /api/v1/conversations?user_id=<user_id>`
- `GET /api/v1/conversations/{conversation_ref}?user_id=<user_id>`

## Prompt por streaming

- `POST /api/v1/session/prompt`
  - body:

```json
{
  "user_id": "demo",
  "conversation_id": "conv-xxxx",
  "codex_session_id": "uuid-opcional",
  "session_id": "conv-xxxx",
  "prompt": "texto usuario",
  "history": [
    { "role": "assistant", "content": "..." },
    { "role": "user", "content": "..." }
  ]
}
```

## Eventos SSE esperados

- `prompt_submitted`
- `token_delta`
- `tool_trace`
- `mode_update`
- `conversation_bound`
- `final_answer`
- `error`

El cliente React debe parsear `data: {...}` y usar el campo `type` del JSON para enrutar la logica.

## Arquitectura recomendada en React

- Stack:
  - React + TypeScript + Vite
  - `fetch` + `ReadableStream` para SSE
- Estructura:
  - `src/app/App.tsx`
  - `src/components/SessionSidebar.tsx`
  - `src/components/ConversationList.tsx`
  - `src/components/ChatTimeline.tsx`
  - `src/components/TracePanel.tsx`
  - `src/components/ReferencesPanel.tsx`
  - `src/services/api.ts`
  - `src/services/sse.ts`
  - `src/types/chat.ts`

## Estado minimo en cliente

- `userId: string`
- `userToken: string`
- `conversations: ConversationSummary[]`
- `activeConversationId: string | null`
- `activeCodexSessionId: string | null`
- `messagesByConversation: Record<string, Message[]>`
- `chatModeByConversation: Record<string, "triage_inicial" | "chat_generico" | "resuelto_por_referencia">`
- `agentStatus: { connected: boolean; busy: boolean } | null`
- `backendStatus: "ok" | "error" | "loading"`
- `pending: boolean`

## Variables de entorno para React

- `VITE_BACKEND_URL=http://localhost:8502`
- `VITE_GATEWAY_URL=http://localhost:9000`
- `VITE_DEFAULT_USER_ID=demo`
- `VITE_DEFAULT_USER_TOKEN=demo-token`

## Plan de migracion por fases

1. Crear `frontend-react` (Vite + TS) sin borrar `frontend` actual.
2. Implementar capa `api.ts` (health, index, status, conversaciones).
3. Implementar `POST /api/v1/session/prompt` con parser SSE.
4. Replicar layout:
   - Sidebar (sesion, health, index, estado agente)
   - Columna de conversaciones
   - Columna de chat
5. Paridad de eventos:
   - `token_delta`: stream incremental
   - `mode_update`: actualizar indicador de modo
   - `conversation_bound`: persistir `codex_session_id`
   - `final_answer`: cerrar respuesta y referencias
6. Smoke test con `tickets_prueba/*.txt`.
7. Cambiar Compose a React cuando la paridad este validada.

## Docker / Compose objetivo

Para el contenedor React:

- Build multi-stage:
  - stage build con Node
  - stage runtime con `nginx:alpine`
- Puerto externo:
  - `8501:80`
- Variables:
  - `VITE_BACKEND_URL=http://backend:8000`
  - `VITE_GATEWAY_URL=http://session-gateway:9000`

## Criterios de aceptacion

- `http://localhost:8501` sirve la UI React.
- Se puede crear y abrir conversaciones.
- Se muestra `Codex Session ID` al hacer `conversation_bound`.
- El primer mensaje refleja `mode_update` (triage o chat).
- El streaming de `token_delta` se ve en vivo.
- `final_answer` guarda mensaje, referencias y token usage.
- Si el agente no esta conectado, se refleja error controlado desde gateway.

## Riesgos y mitigacion

- Riesgo: implementar chat contra `/api/v1/chat/` y perder funcionalidad real.
  - Mitigacion: usar exclusivamente `/api/v1/session/prompt` para la conversacion de UI.
- Riesgo: manejo incorrecto de `conversation_bound`.
  - Mitigacion: actualizar `activeCodexSessionId` y refrescar lista de conversaciones.
- Riesgo: diferencias de estado respecto a Streamlit.
  - Mitigacion: mantener `messagesByConversation` y `chatModeByConversation` como fuentes unicas de verdad.

## Checklist final

- React replica flujo `session-gateway` + SSE.
- Autenticacion bearer aplicada a endpoints del gateway.
- Conversaciones persistidas visibles y navegables.
- Indexacion de conocimiento funcional.
- Manejo de errores (HTTP y eventos `error`) visible en UI.
- Compose preparado para alternar de Streamlit a React.
