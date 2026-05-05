import json
import os
import uuid
from typing import Any, Dict, List

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://session-gateway:9000")

st.set_page_config(page_title="Asistente IA", page_icon="*", layout="wide")
st.title("Asistente de Soporte - Streamlit + Codex CLI")

st.sidebar.markdown("---")
st.sidebar.subheader("Sesion Codex Local")

default_user_id = os.environ.get("DEFAULT_USER_ID", "demo")
default_user_token = os.environ.get("DEFAULT_USER_TOKEN", "demo-token")
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = f"streamlit-{uuid.uuid4().hex[:8]}"
if "chat_mode_by_session" not in st.session_state:
    st.session_state.chat_mode_by_session = {}

user_id = st.sidebar.text_input("User ID", value=default_user_id)
user_token = st.sidebar.text_input("User Token", value=default_user_token, type="password")
session_id = st.sidebar.text_input("Session ID", value=st.session_state.active_session_id)
st.session_state.active_session_id = session_id.strip() or st.session_state.active_session_id
session_id = st.session_state.active_session_id

headers = {"Authorization": f"Bearer {user_token}"}
mode_by_session: Dict[str, str] = st.session_state.chat_mode_by_session
current_mode = mode_by_session.get(session_id, "triage_inicial")
mode_label_map = {
    "triage_inicial": "Triage inicial",
    "chat_generico": "Chat generico",
    "resuelto_por_referencia": "Resuelto por referencia",
}
mode_indicator = st.sidebar.empty()
mode_indicator.info(f"Modo actual: {mode_label_map.get(current_mode, current_mode)}")

st.sidebar.markdown("---")
st.sidebar.subheader("Gestion de Conocimiento")

if st.sidebar.button("Indexar Obsidian Vault"):
    with st.spinner("Indexando base de conocimiento..."):
        try:
            res = requests.post(f"{BACKEND_URL}/api/v1/knowledge/index", timeout=180)
            result = res.json()
            if result.get("success"):
                st.sidebar.success(f"{result['message']}")
            else:
                st.sidebar.warning(result.get("message", "Indexacion fallida."))
        except Exception as e:
            st.sidebar.error(f"Error al indexar: {e}")

try:
    health = requests.get(f"{BACKEND_URL}/health", timeout=3)
    if health.status_code == 200:
        st.sidebar.success("Backend conectado")
    else:
        st.sidebar.error("Backend no responde")
except Exception:
    st.sidebar.error("Backend no disponible")

try:
    status = requests.get(
        f"{GATEWAY_URL}/api/v1/agents/{user_id}/status",
        headers=headers,
        timeout=4,
    )
    if status.status_code == 200:
        status_json = status.json()
        if status_json.get("connected"):
            label = "Conectado y ocupado" if status_json.get("busy") else "Conectado y libre"
            st.sidebar.success(f"Agente local: {label}")
        else:
            st.sidebar.warning("Agente local no conectado")
    else:
        st.sidebar.error(f"Gateway status error: {status.text[:120]}")
except Exception as e:
    st.sidebar.error(f"Gateway no disponible: {e}")

st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hola. Envia un ticket. Se consultara ChromaDB via MCP y, "
                "si no hay resolucion previa, Codex continuara en modo conversacional."
            ),
            "references": [],
        }
    ]

def _render_token_usage(token_usage: Dict[str, Any] | None):
    if not isinstance(token_usage, dict):
        return
    input_tokens = int(token_usage.get("input_tokens", 0))
    output_tokens = int(token_usage.get("output_tokens", 0))
    total_tokens = int(token_usage.get("total_tokens", input_tokens + output_tokens))
    method = str(token_usage.get("method", "unknown"))
    st.caption(
        f"Tokens (iteracion): entrada={input_tokens} salida={output_tokens} total={total_tokens} metodo={method}"
    )


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        _render_token_usage(message.get("token_usage"))
        refs = message.get("references") or []
        if refs:
            with st.expander("Referencias"):
                for ref in refs:
                    source = ref.get("source", "unknown")
                    ticket_id = ref.get("ticket_id")
                    snippet = ref.get("snippet", "")
                    label = f"{ticket_id} ({source})" if ticket_id else str(source)
                    st.markdown(f"- `{label}`")
                    if snippet:
                        st.caption(snippet)


def _parse_sse_line(line: str) -> Dict[str, Any] | None:
    if not line.startswith("data:"):
        return None
    payload = line.split("data:", 1)[1].strip()
    if not payload:
        return None
    return json.loads(payload)


if user_input := st.chat_input("Escribe el ticket o tu mensaje aqui..."):
    st.session_state.messages.append({"role": "user", "content": user_input, "references": []})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        trace_box = st.expander("Trazas MCP/Codex", expanded=False)
        refs_box = st.expander("Referencias", expanded=False)
        token_box = st.expander("Uso de tokens", expanded=False)

        accumulated = ""
        traces: List[str] = []
        references: List[Dict[str, Any]] = []
        token_usage: Dict[str, Any] | None = None

        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "prompt": user_input,
            "history": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in st.session_state.messages
            ],
        }

        try:
            with requests.post(
                f"{GATEWAY_URL}/api/v1/session/prompt",
                json=payload,
                headers=headers,
                stream=True,
                timeout=300,
            ) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"{response.status_code}: {response.text[:500]}")

                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    event = _parse_sse_line(raw_line)
                    if not event:
                        continue

                    event_type = event.get("type")
                    if event_type == "token_delta":
                        accumulated += event.get("delta", "")
                        placeholder.markdown(accumulated)
                        continue

                    if event_type == "tool_trace":
                        detail = event.get("detail", "")
                        if detail:
                            traces.append(detail)
                            with trace_box:
                                st.markdown("\n\n".join(traces[-20:]))
                        continue

                    if event_type == "mode_update":
                        mode = str(event.get("mode", "")).strip()
                        if mode:
                            mode_by_session[session_id] = mode
                            label = mode_label_map.get(mode, mode)
                            mode_indicator.info(f"Modo actual: {label}")
                            traces.append(f"[mode_update] {label}")
                            with trace_box:
                                st.markdown("\n\n".join(traces[-20:]))
                        continue

                    if event_type == "final_answer":
                        answer = event.get("answer", "")
                        if answer:
                            accumulated = answer
                            placeholder.markdown(accumulated)
                        token_usage = event.get("token_usage")
                        with token_box:
                            _render_token_usage(token_usage)
                        references = event.get("references", []) or []
                        if references:
                            with refs_box:
                                for ref in references:
                                    source = ref.get("source", "unknown")
                                    ticket_id = ref.get("ticket_id")
                                    snippet = ref.get("snippet", "")
                                    label = f"{ticket_id} ({source})" if ticket_id else str(source)
                                    st.markdown(f"- `{label}`")
                                    if snippet:
                                        st.caption(snippet)
                        continue

                    if event_type == "error":
                        msg = event.get("message", "Error desconocido.")
                        st.error(msg)
                        break

            if not accumulated:
                accumulated = "No se recibio contenido de Codex."
                placeholder.markdown(accumulated)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": accumulated,
                    "references": references,
                    "token_usage": token_usage,
                }
            )
        except Exception as e:
            st.error(f"Error de procesamiento: {e}")
