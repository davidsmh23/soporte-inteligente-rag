# Manual de Usuario: Asistente de Soporte + Codex CLI

## 1. Objetivo

Este manual explica como:

1. Levantar la plataforma con Docker.
2. Conectar el agente local de Codex.
3. Usar el flujo RAG determinista en la web.

## 2. Flujo funcional actual

1. El usuario escribe un ticket en Streamlit.
2. `local_agent` ejecuta primero `support_lookup_ticket` via MCP.
3. Si `resolved=true` (Top-1 + umbral), devuelve solucion previa con:
   - `ticket_id` original
   - archivo `.md`
   - pasos completos de `# Solucion Exitosa`
4. Si `resolved=false`, se usa Codex en modo conversacional normal.

## 3. Arquitectura y puertos

- Frontend Streamlit: `http://185.57.173.233:8501`
- Backend API: `http://185.57.173.233:8502`
- Swagger backend: `http://185.57.173.233:8502/docs`
- MCP server: `http://185.57.173.233:8100`
- Session gateway: `http://185.57.173.233:9000`
- ChromaDB: `http://185.57.173.233:8033`

## 4. Requisitos

### Servidor

- Docker Desktop o Docker Engine + Compose.
- Archivo `.env` en la raiz del repo.

### Cliente local (usuario)

- Codex CLI instalado y autenticado.
- Python 3.10+.
- Acceso de red al servidor (`8501`, `9000`, `8100`).

## 5. Configuracion del servidor

1. Crear `.env`:

```bash
cp .env.example .env
```

2. Definir valores minimos:

```env
EMBEDDING_API_KEY=<tu_clave_embeddings>
MCP_BEARER_TOKEN=<token_fuerte_mcp>
SESSION_USER_TOKENS=demo:demo-token
DEFAULT_USER_ID=demo
DEFAULT_USER_TOKEN=demo-token
```

3. Levantar servicios:

```bash
docker compose up -d --build
```

4. Verificar salud:

```bash
curl http://185.57.173.233:8502/health
curl http://185.57.173.233:8100/health
curl http://185.57.173.233:9000/health
```

## 6. Conectar el agente local Codex

En el equipo del usuario:

```bash
cd local_agent
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instalar dependencia:

```bash
pip install -r requirements.txt
```

Variables recomendadas (anonimizadas):

Linux/macOS:

```bash
export SESSION_GATEWAY_WS_URL="ws://185.57.173.233:9000/ws/agent"
export SESSION_USER_ID="<USER_ID>"
export SESSION_USER_TOKEN="<SESSION_USER_TOKEN>"
export SUPPORT_MCP_URL="http://185.57.173.233:8100/mcp"
export SUPPORT_MCP_TOKEN="<SUPPORT_MCP_TOKEN>"
```

PowerShell:

```powershell
$env:SESSION_GATEWAY_WS_URL="ws://185.57.173.233:9000/ws/agent"
$env:SESSION_USER_ID="<USER_ID>"
$env:SESSION_USER_TOKEN="<SESSION_USER_TOKEN>"
$env:SUPPORT_MCP_URL="http://185.57.173.233:8100/mcp"
$env:SUPPORT_MCP_TOKEN="<SUPPORT_MCP_TOKEN>"
```

Arranque:

```bash
python main.py
```

Nota: si `SUPPORT_MCP_TOKEN` no se exporta, `local_agent` intenta leer `MCP_BEARER_TOKEN` desde `../.env`.

Ejemplo completo de arranque (anonimizado):

Linux/macOS:

```bash
cd "/ruta/al/repositorio/soporte-inteligente-rag/local_agent"
source .venv/bin/activate

export SESSION_GATEWAY_WS_URL="ws://185.57.173.233:9000/ws/agent"
export SESSION_USER_ID="<USER_ID>"
export SESSION_USER_TOKEN="<SESSION_USER_TOKEN>"
export SUPPORT_MCP_URL="http://185.57.173.233:8100/mcp"
export SUPPORT_MCP_TOKEN="<SUPPORT_MCP_TOKEN>"

python main.py
```

Windows (PowerShell):

```powershell
cd "C:\ruta\al\repositorio\soporte-inteligente-rag\local_agent"
.venv\Scripts\Activate.ps1

$env:SESSION_GATEWAY_WS_URL="ws://185.57.173.233:9000/ws/agent"
$env:SESSION_USER_ID="<USER_ID>"
$env:SESSION_USER_TOKEN="<SESSION_USER_TOKEN>"
$env:SUPPORT_MCP_URL="http://185.57.173.233:8100/mcp"
$env:SUPPORT_MCP_TOKEN="<SUPPORT_MCP_TOKEN>"

python main.py
```

## 7. Uso diario en Streamlit

1. Abrir `http://185.57.173.233:8501`.
2. Completar sidebar:
   - `User ID`
   - `User Token`
   - `Session ID`
3. Confirmar estado:
   - `Backend conectado`
   - `Agente local: Conectado y libre`
4. Pulsar `Indexar Obsidian Vault` cuando cambie la base de conocimiento.
5. Enviar ticket.

Resultado esperado:

- Ticket conocido: respuesta con `ticket_id + archivo + solucion completa`.
- Ticket no conocido: respuesta conversacional de Codex.

## 8. Solucion de problemas

### Error `Lookup MCP fallo: HTTP Error 422`

Causa habitual: `mcp_server` desactualizado o endpoint `/mcp` sin leer body JSON.

Accion:

```bash
docker compose up -d --build mcp-server
```

### `Invalid user token` en gateway

- Revisar `SESSION_USER_TOKENS` en servidor.
- Revisar `SESSION_USER_TOKEN` en cliente.
- En llamadas HTTP usar cabecera `Authorization: Bearer <token>`.

### `Backend no disponible`

```bash
docker compose logs --tail 200 backend
```

### Agente local no conectado

- Verificar que `python main.py` sigue corriendo.
- Comprobar URL `ws://.../ws/agent`.
- Probar estado:

```bash
curl -H "Authorization: Bearer <token>" http://185.57.173.233:9000/api/v1/agents/demo/status
```

### No salen referencias aunque hay match

- Reindexar vault.
- Comprobar `EMBEDDING_API_KEY`.
- Revisar en UI el bloque `Trazas MCP/Codex`.

## 9. Operacion recomendada

- Usar token distinto por usuario.
- Rotar `MCP_BEARER_TOKEN` periodicamente.
- Usar reverse proxy HTTPS en produccion.
- Monitorizar logs de `frontend`, `backend`, `mcp-server`, `session-gateway`, `local_agent`.

