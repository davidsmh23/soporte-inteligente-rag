# Cambio entre modo local y modo servidor

Este documento explica como usar la misma base de codigo en dos modos:

- Modo local/original (`localhost`).
- Modo servidor remoto (por ejemplo `192.168.1.65`).

No hace falta cambiar codigo para alternar entre modos. Solo variables de entorno al lanzar `local_agent`.

## 1) Arrancar Docker Compose

Desde la raiz del repo:

```powershell
docker compose up -d --build
```

Puertos publicados por defecto:

- Frontend: `8501`
- Backend: `8502`
- MCP: `8100`
- Session Gateway: `9000`

## 2) Modo local/original (version inicial)

Usa este modo cuando el `local_agent` corre en la misma maquina donde esta Docker Compose.

```powershell
cd "C:\Users\DavidSanMartinHurtad\OneDrive - Habber Tec\Documentos\GitHub\soporte-inteligente-rag\local_agent"
.venv\Scripts\Activate.ps1

$env:SESSION_GATEWAY_WS_URL="ws://localhost:9000/ws/agent"
$env:SESSION_USER_ID="demo"
$env:SESSION_USER_TOKEN="Qm7xR4nP9vK2sL8dT5yH3cW1fJ6bN0zA"
$env:SUPPORT_MCP_URL="http://localhost:8100/mcp"
$env:SUPPORT_MCP_TOKEN="3kV9pL2xT7mQ4dR8nY1hC6sF0bW5jZ"

python main.py
```

UI:

- `http://localhost:8501`

## 3) Modo servidor remoto

Usa este modo cuando el `local_agent` corre en otra maquina distinta al servidor Docker.

```powershell
cd "C:\Users\DavidSanMartinHurtad\OneDrive - Habber Tec\Documentos\GitHub\soporte-inteligente-rag\local_agent"
.venv\Scripts\Activate.ps1

$env:SESSION_GATEWAY_WS_URL="ws://192.168.1.65:9000/ws/agent"
$env:SESSION_USER_ID="demo"
$env:SESSION_USER_TOKEN="Qm7xR4nP9vK2sL8dT5yH3cW1fJ6bN0zA"
$env:SUPPORT_MCP_URL="http://192.168.1.65:8100/mcp"
$env:SUPPORT_MCP_TOKEN="3kV9pL2xT7mQ4dR8nY1hC6sF0bW5jZ"

python main.py
```

UI:

- `http://192.168.1.65:8501`

## 4) Volver a la version inicial rapidamente

Opcion A: cerrar la terminal y abrir una nueva.

Opcion B: limpiar variables y volver a `localhost`:

```powershell
Remove-Item Env:SESSION_GATEWAY_WS_URL -ErrorAction SilentlyContinue
Remove-Item Env:SUPPORT_MCP_URL -ErrorAction SilentlyContinue

$env:SESSION_GATEWAY_WS_URL="ws://localhost:9000/ws/agent"
$env:SUPPORT_MCP_URL="http://localhost:8100/mcp"
```

## 5) Comprobaciones utiles

Desde el cliente:

```powershell
Test-NetConnection 192.168.1.65 -Port 9000
Test-NetConnection 192.168.1.65 -Port 8100
```

Desde el servidor:

```bash
docker compose ps
docker compose logs --tail 100 session-gateway mcp-server frontend
```

Si en la UI aparece `Agente local no conectado`, normalmente el problema es:

- `SESSION_USER_ID` o token distinto entre UI y `local_agent`.
- URL apuntando a `localhost` cuando el servidor esta en otra maquina.
- `local_agent` no esta corriendo en segundo plano.
