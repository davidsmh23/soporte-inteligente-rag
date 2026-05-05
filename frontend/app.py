import json
import os
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

user_id = st.sidebar.text_input("User ID", value=default_user_id)
user_token = st.sidebar.text_input("User Token", value=default_user_token, type="password")
headers = {"Authorization": f"Bearer {user_token}"}

mode_label_map = {
    "triage_inicial": "Triage inicial",
    "chat_generico": "Chat generico",
    "resuelto_por_referencia": "Resuelto por referencia",
}

if "messages_by_conversation" not in st.session_state:
    st.session_state.messages_by_conversation = {}
if "chat_mode_by_conversation" not in st.session_state:
    st.session_state.chat_mode_by_conversation = {}
if "conversations" not in st.session_state:
    st.session_state.conversations = []
if "active_conversation_id" not in st.session_state:
    st.session_state.active_conversation_id = None
if "active_codex_session_id" not in st.session_state:
    st.session_state.active_codex_session_id = None
if "ui_error" not in st.session_state:
    st.session_state.ui_error = None


def _welcome_message() -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": (
            "Hola. Crea o selecciona una conversacion. "
            "Todos los mensajes de esta conversacion iran al mismo hilo real de Codex."
        ),
        "references": [],
        "token_usage": None,
    }


def _parse_sse_line(line: str) -> Dict[str, Any] | None:
    if not line.startswith("data:"):
        return None
    payload = line.split("data:", 1)[1].strip()
    if not payload:
        return None
    return json.loads(payload)


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


def _request_json(method: str, url: str, **kwargs) -> requests.Response:
    return requests.request(method=method, url=url, headers=headers, timeout=10, **kwargs)


def _refresh_conversations():
    res = _request_json("GET", f"{GATEWAY_URL}/api/v1/conversations", params={"user_id": user_id})
    if res.status_code != 200:
        raise RuntimeError(f"{res.status_code}: {res.text[:300]}")
    payload = res.json()
    st.session_state.conversations = payload.get("conversations", []) or []


def _create_conversation(title: str = "Nueva conversacion") -> dict[str, Any]:
    res = _request_json(
        "POST",
        f"{GATEWAY_URL}/api/v1/conversations",
        json={"user_id": user_id, "title": title},
    )
    if res.status_code != 200:
        raise RuntimeError(f"{res.status_code}: {res.text[:300]}")
    return res.json()


def _load_conversation(conversation_ref: str):
    res = _request_json(
        "GET",
        f"{GATEWAY_URL}/api/v1/conversations/{conversation_ref}",
        params={"user_id": user_id},
    )
    if res.status_code != 200:
        raise RuntimeError(f"{res.status_code}: {res.text[:300]}")

    detail = res.json()
    conversation_id = detail["conversation_id"]
    messages = detail.get("messages", [])
    st.session_state.messages_by_conversation[conversation_id] = messages or [_welcome_message()]
    st.session_state.active_conversation_id = conversation_id
    st.session_state.active_codex_session_id = detail.get("codex_session_id")


def _ensure_active_conversation():
    active = st.session_state.active_conversation_id
    if active:
        return

    try:
        _refresh_conversations()
    except Exception:
        st.session_state.conversations = []

    if st.session_state.conversations:
        first = st.session_state.conversations[0]
        st.session_state.active_conversation_id = first.get("conversation_id")
        st.session_state.active_codex_session_id = first.get("codex_session_id")
        conv_id = st.session_state.active_conversation_id
        if conv_id and conv_id not in st.session_state.messages_by_conversation:
            try:
                _load_conversation(conv_id)
            except Exception:
                st.session_state.messages_by_conversation[conv_id] = [_welcome_message()]
        return

    created = _create_conversation("Nueva conversacion")
    conv_id = created["conversation_id"]
    st.session_state.active_conversation_id = conv_id
    st.session_state.active_codex_session_id = created.get("codex_session_id")
    st.session_state.messages_by_conversation[conv_id] = [_welcome_message()]
    _refresh_conversations()


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

_ensure_active_conversation()

try:
    _refresh_conversations()
except Exception as e:
    st.session_state.ui_error = f"No se pudo cargar conversaciones: {e}"

if st.session_state.ui_error:
    st.warning(st.session_state.ui_error)

left_col, right_col = st.columns([2.3, 1])

with right_col:
    st.subheader("Conversaciones")
    if st.button("Nueva conversacion", use_container_width=True):
        try:
            created = _create_conversation("Nueva conversacion")
            conv_id = created["conversation_id"]
            st.session_state.active_conversation_id = conv_id
            st.session_state.active_codex_session_id = created.get("codex_session_id")
            st.session_state.messages_by_conversation[conv_id] = [_welcome_message()]
            _refresh_conversations()
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo crear conversacion: {e}")

    conversations: List[Dict[str, Any]] = st.session_state.conversations
    if not conversations:
        st.caption("Sin conversaciones guardadas todavia.")
    else:
        for conv in conversations:
            conv_id = conv.get("conversation_id", "")
            codex_id = conv.get("codex_session_id") or "(pendiente bind)"
            title = conv.get("title") or "Conversacion"
            stamp = conv.get("last_message_at") or conv.get("created_at") or ""
            status = conv.get("status") or "unknown"
            label = f"{title}\n{codex_id}\n{stamp[:19]} | {status}"
            if st.button(label, key=f"conv_{conv_id}", use_container_width=True):
                try:
                    _load_conversation(conv_id)
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo abrir conversacion: {e}")

with left_col:
    active_conversation_id = st.session_state.active_conversation_id
    active_codex_session_id = st.session_state.active_codex_session_id

    if not active_conversation_id:
        st.info("Crea una conversacion para empezar.")
        st.stop()

    current_mode = st.session_state.chat_mode_by_conversation.get(active_conversation_id, "chat_generico")
    mode_label = mode_label_map.get(current_mode, current_mode)

    st.markdown(
        f"**Conversacion activa:** `{active_conversation_id}`  \\\n"
        f"**Codex Session ID:** `{active_codex_session_id or 'Creando sesion Codex...'}`  \\\n"
        f"**Modo:** `{mode_label}`"
    )
    st.markdown("---")

    if active_conversation_id not in st.session_state.messages_by_conversation:
        st.session_state.messages_by_conversation[active_conversation_id] = [_welcome_message()]

    messages = st.session_state.messages_by_conversation[active_conversation_id]
    if not messages:
        messages = [_welcome_message()]
        st.session_state.messages_by_conversation[active_conversation_id] = messages

    for message in messages:
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

user_input = st.chat_input("Escribe tu mensaje...")
if user_input and st.session_state.active_conversation_id:
    active_conversation_id = st.session_state.active_conversation_id
    active_codex_session_id = st.session_state.active_codex_session_id
    messages = st.session_state.messages_by_conversation.get(active_conversation_id, [_welcome_message()])
    messages.append({"role": "user", "content": user_input, "references": [], "token_usage": None})
    st.session_state.messages_by_conversation[active_conversation_id] = messages

    with left_col:
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
                "conversation_id": active_conversation_id,
                "codex_session_id": active_codex_session_id,
                "session_id": active_conversation_id,
                "prompt": user_input,
                "history": [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in messages
                    if msg.get("role") in {"user", "assistant"}
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
                                st.session_state.chat_mode_by_conversation[active_conversation_id] = mode
                                label = mode_label_map.get(mode, mode)
                                traces.append(f"[mode_update] {label}")
                                with trace_box:
                                    st.markdown("\n\n".join(traces[-20:]))
                            continue

                        if event_type == "conversation_bound":
                            bound_conv_id = str(event.get("conversation_id") or active_conversation_id)
                            bound_codex = str(event.get("codex_session_id") or "").strip() or None
                            if bound_conv_id == active_conversation_id and bound_codex:
                                st.session_state.active_codex_session_id = bound_codex
                                active_codex_session_id = bound_codex
                                traces.append(f"[conversation_bound] {bound_codex}")
                                with trace_box:
                                    st.markdown("\n\n".join(traces[-20:]))
                                try:
                                    _refresh_conversations()
                                except Exception:
                                    pass
                            continue

                        if event_type == "final_answer":
                            bound_codex_in_final = str(event.get("codex_session_id") or "").strip() or None
                            if bound_codex_in_final and not st.session_state.active_codex_session_id:
                                st.session_state.active_codex_session_id = bound_codex_in_final
                                active_codex_session_id = bound_codex_in_final
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

                messages.append(
                    {
                        "role": "assistant",
                        "content": accumulated,
                        "references": references,
                        "token_usage": token_usage,
                    }
                )
                st.session_state.messages_by_conversation[active_conversation_id] = messages
                try:
                    _refresh_conversations()
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Error de procesamiento: {e}")
