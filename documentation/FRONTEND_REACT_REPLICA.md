# Frontend Actual y Guia de Replica en React

## 1) Tecnologias usadas en el frontend actual

- **Framework UI**: `Streamlit 1.32.0`
- **HTTP client**: `requests 2.31.0`
- **Lenguaje**: `Python 3.10` (contenedor del frontend)
- **Modelo de ejecucion**: app server-side de Streamlit (`streamlit run app.py`)
- **Transporte en tiempo real**: `SSE` (Server-Sent Events) consumido con `requests.post(..., stream=True)`
- **Despliegue**: contenedor Docker, puerto `8501`

## 2) Tecnicas aplicadas en la UI actual

- **Estado conversacional en memoria** con `st.session_state.messages`.
- **Render incremental de respuesta** por llegada de tokens (`token_delta`) para efecto streaming.
- **Manejo de eventos tipados SSE**:
  - `token_delta`
  - `tool_trace`
  - `final_answer`
  - `error`
- **Panel de configuracion de sesion** (user id, token, session id) en sidebar.
- **Health checks en vivo** contra backend y session-gateway.
- **Accion operacional desde UI**: boton para indexar base de conocimiento.
- **Trazabilidad**: bloque expandible con trazas MCP/Codex.
- **Referencias de soporte**: bloque expandible con tickets y snippets de evidencia.
- **Fallback de errores** con mensajes controlados para HTTP y parsing/eventos.

## 3) Componentes funcionales del frontend actual

- **Header principal** con titulo de la aplicacion.
- **Sidebar de sesion**:
  - Input `User ID`
  - Input `User Token` (password)
  - Input `Session ID`
  - Estado de backend
  - Estado de agente local
  - Boton `Indexar Obsidian Vault`
- **Timeline de chat**:
  - Mensajes `user`
  - Mensajes `assistant`
- **Input de chat** (prompt/ticket)
- **Zona de respuesta en streaming**
- **Expander de trazas**
- **Expander de referencias**

## 4) Mapeo 1:1 para React

- `st.session_state.messages` -> `useState<Message[]>`
- `st.chat_input(...)` -> `<form>` + `<input/>` o `<textarea/>`
- `st.chat_message(role)` -> componente `<ChatMessage role="..." />`
- `st.expander(...)` -> `<details>` nativo o componente Accordion
- `st.sidebar.*` -> layout con `<aside>`
- `requests.get/post` -> `fetch` o `axios`
- `iter_lines` SSE manual -> `ReadableStream` + parser de lineas `data:`
- `st.spinner` -> indicador `loading` en boton/overlay
- `st.success/warning/error` -> sistema de alertas/toasts

## 5) Contratos API que debe respetar la version React

- `GET /health` del backend.
- `GET /api/v1/agents/{user_id}/status` con header `Authorization: Bearer <token>`.
- `POST /api/v1/knowledge/index`.
- `POST /api/v1/session/prompt` con body:

```json
{
  "user_id": "demo",
  "session_id": "streamlit-session",
  "prompt": "texto usuario",
  "history": [
    { "role": "assistant", "content": "..." },
    { "role": "user", "content": "..." }
  ]
}
```

## 6) Esqueleto recomendado en React

```text
src/
  app/
    App.tsx
  components/
    SessionSidebar.tsx
    ChatTimeline.tsx
    ChatMessage.tsx
    ChatInput.tsx
    TracePanel.tsx
    ReferencesPanel.tsx
    StatusBadges.tsx
  hooks/
    useSessionConfig.ts
    useHealthStatus.ts
    usePromptStream.ts
  services/
    api.ts
    sseParser.ts
  types/
    chat.ts
    events.ts
```

## 7) Logica minima que Codex debe implementar al replicar

1. Crear estado de sesion (`userId`, `userToken`, `sessionId`) con valores por defecto via variables de entorno.
2. Cargar mensaje inicial del asistente.
3. Implementar checks de salud de backend y agente al montar.
4. Enviar prompt a `/api/v1/session/prompt` con historial.
5. Parsear stream SSE por linea (`data: { ...json... }`).
6. Actualizar respuesta en vivo en `token_delta`.
7. Acumular trazas en `tool_trace` y mostrarlas en panel colapsable.
8. Reemplazar respuesta final y referencias en `final_answer`.
9. Gestionar `error` y errores de red con mensajes visibles.
10. Persistir mensajes en estado para mantener continuidad del chat.

## 8) Prompt sugerido para otro Codex (copia/pega)

```text
Replica el frontend actual de Streamlit en React + TypeScript con comportamiento funcional equivalente.

Requisitos obligatorios:
- Sidebar con User ID, User Token (password), Session ID.
- Boton para POST /api/v1/knowledge/index.
- Indicadores de estado:
  - GET {BACKEND_URL}/health
  - GET {GATEWAY_URL}/api/v1/agents/{user_id}/status con Bearer token
- Chat con historial en memoria.
- Envio de prompt a POST {GATEWAY_URL}/api/v1/session/prompt.
- Consumo de respuesta por SSE:
  - token_delta: render incremental
  - tool_trace: panel de trazas
  - final_answer: mensaje final + referencias
  - error: alerta visible
- UI con layout: sidebar + zona principal de chat.
- Codigo modular por componentes, hooks y services.

No cambies contratos de API ni nombres de campos del payload.
```
