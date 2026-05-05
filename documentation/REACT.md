# Migracion de Frontend a React

## Estado actual del proyecto

El frontend actual esta en `frontend/app.py` (Streamlit) y usa estos endpoints:

- `GET /health` para estado backend.
- `POST /api/v1/knowledge/index` para indexar el vault.
- `POST /api/v1/chat/` para chat con triage y conversacion.

El contrato actual de chat es:

- Request:
  - `messages: [{ role: "user" | "assistant", content: string }]`
- Response:
  - `response: string`
  - `route: "rag" | "free_chat" | "conversation"`
  - `sources: string[]`

## Objetivo de la migracion

Sustituir Streamlit por una SPA React manteniendo el mismo flujo funcional:

1. Sidebar con estado backend e indexacion de conocimiento.
2. Chat con historial local.
3. Envio del historial a `/api/v1/chat/`.
4. Visualizacion de `sources` cuando existan.

No se cambia backend en esta fase.

## Arquitectura propuesta (React)

- Stack recomendado:
  - React + TypeScript + Vite
  - Fetch API nativa (sin libreria adicional)
  - Estado local con `useState`
- Estructura recomendada:
  - `src/App.tsx`
  - `src/components/Sidebar.tsx`
  - `src/components/ChatWindow.tsx`
  - `src/components/MessageList.tsx`
  - `src/components/Composer.tsx`
  - `src/api/client.ts`
  - `src/types/chat.ts`

## Variables de entorno (frontend React)

Definir en `frontend/.env`:

- `VITE_BACKEND_URL=http://localhost:8502`

En Docker Compose, exponer esta variable al contenedor React.

## Implementacion funcional

### 1) Tipos y cliente API

Crear tipos:

- `ChatRole = "user" | "assistant"`
- `ChatMessage = { role: ChatRole; content: string }`
- `ChatResponse = { response: string; route: "rag" | "free_chat" | "conversation"; sources: string[] }`

Crear funciones:

- `healthCheck(): Promise<boolean>`
- `indexKnowledge(): Promise<{ success: boolean; message: string }>`
- `sendChat(messages: ChatMessage[]): Promise<ChatResponse>`

### 2) Estado de UI

Gestionar en `App`:

- `messages: ChatMessage[]`
- `backendStatus: "ok" | "error" | "loading"`
- `indexing: boolean`
- `indexMessage: string`
- `pending: boolean`

Inicializar con mensaje de bienvenida:

- Assistant: "Hola. Envia un ticket..."

### 3) Envio de chat

Al enviar un mensaje:

1. Agregar mensaje `user` al estado.
2. Construir `apiMessages` filtrando la bienvenida inicial del assistant.
3. Llamar `sendChat(apiMessages)`.
4. Agregar mensaje `assistant` con `response`.
5. Si `sources` existe y tiene elementos, mostrarlas en bloque de referencias.

### 4) Sidebar

Incluir:

- Estado backend en tiempo real (`healthCheck` al montar y boton manual refrescar).
- Boton `Indexar Obsidian Vault`.
- Resultado de indexacion (`success/warning/error`).

### 5) UX minima equivalente

- Input bloqueado mientras `pending=true`.
- Scroll automatico al ultimo mensaje.
- Mensajes de error de red visibles.

## Plan de despliegue Docker

1. Reemplazar `frontend` Streamlit por `frontend-react`.
2. Nuevo `frontend-react/Dockerfile`:
   - Build Vite
   - Servir estaticos con `nginx:alpine`
3. Actualizar `docker-compose.yml`:
   - `build.context: ./frontend-react`
   - `ports: "8501:80"`
   - `environment: VITE_BACKEND_URL=http://backend:8000`

## Criterios de aceptacion

- `http://localhost:8501` abre frontend React.
- `Backend conectado` visible si `/health` responde 200.
- `Indexar Obsidian Vault` funciona y muestra resultado.
- Primer ticket ejecuta triage (`rag` o `free_chat`) sin errores.
- Mensajes posteriores usan ruta `conversation`.
- Referencias (`sources`) se muestran cuando vienen en respuesta.

## Riesgos y mitigacion

- CORS en backend:
  - Si frontend y backend van en distinto origen, habilitar CORS en FastAPI.
- Diferencias de estado vs Streamlit:
  - Mantener exactamente el filtro de bienvenida antes de enviar historial.
- Timeouts:
  - Configurar timeout de chat en cliente (60s inicial).

## Checklist de migracion

- Crear proyecto React + TypeScript.
- Implementar cliente API y tipos.
- Implementar sidebar (health + index).
- Implementar chat (historial, envio, errores, referencias).
- Actualizar Docker y Compose.
- Prueba manual con `tickets_prueba`.
