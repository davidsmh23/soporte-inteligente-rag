import os

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8502")

st.set_page_config(page_title="Asistente IA", page_icon="✨", layout="wide")
st.title("✨ Asistente de Soporte - Powered by Gemini")

# --- Sidebar ---
st.sidebar.markdown("---")
st.sidebar.subheader("Gestión de Conocimiento")

if st.sidebar.button("🔄 Indexar Obsidian Vault"):
    with st.spinner("Indexando base de conocimiento..."):
        try:
            res = requests.post(f"{BACKEND_URL}/api/v1/knowledge/index", timeout=120)
            result = res.json()
            if result.get("success"):
                st.sidebar.success(f"✅ {result['message']}")
            else:
                st.sidebar.warning(result.get("message", "Indexación fallida."))
        except Exception as e:
            st.sidebar.error(f"❌ Error al indexar: {e}")

try:
    health = requests.get(f"{BACKEND_URL}/health", timeout=3)
    if health.status_code == 200:
        st.sidebar.success("✅ Backend conectado")
    else:
        st.sidebar.error("❌ Backend no responde")
except Exception:
    st.sidebar.error("❌ Backend no disponible")

# --- Chat ---
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 ¡Hola! Soy Codex. Pega aquí el ticket de soporte y revisaré si ya lo hemos resuelto antes en Obsidian.",
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Escribe el ticket o tu mensaje aquí..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                # Filter out the initial welcome message before sending to backend.
                # This ensures the backend receives len==1 for the first ticket (triage).
                api_messages = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in st.session_state.messages
                    if not (msg["role"] == "assistant" and msg["content"].startswith("👋"))
                ]

                res = requests.post(
                    f"{BACKEND_URL}/api/v1/chat/",
                    json={"messages": api_messages},
                    timeout=60,
                )
                result = res.json()

                ai_response = result["response"]
                sources = result.get("sources", [])

                st.markdown(ai_response)

                if sources:
                    with st.expander("📚 Fuentes consultadas"):
                        for source in sources:
                            st.markdown(f"- `{source}`")

                st.session_state.messages.append({"role": "assistant", "content": ai_response})

            except Exception as e:
                st.error(f"❌ Error de procesamiento: {e}")
