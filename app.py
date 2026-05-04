import streamlit as st
import chromadb
import os

# Importaciones de LangChain 
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

# 1. Configuración de la interfaz
st.set_page_config(page_title="Asistente IA", page_icon="✨", layout="wide")
st.title("✨ Asistente de Soporte - Powered by Gemini")

# Obtenemos la clave de API
google_api_key = os.environ.get("GOOGLE_API_KEY")

# 2. Conexión a ChromaDB (Docker)
chroma_client = None
try:
    chroma_client = chromadb.HttpClient(host=os.environ.get("CHROMA_SERVER_HOST", "chromadb"), port=8000)
    st.sidebar.success("✅ Conectado a ChromaDB")
except Exception as e:
    st.sidebar.error(f"❌ Error conectando a ChromaDB: {e}")

# Inicializamos Embeddings
if google_api_key and google_api_key != "tu_clave_de_gemini_aqui":
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2", google_api_key=google_api_key)
else:
    embeddings = None

# Conectamos LangChain con ChromaDB
if embeddings and chroma_client:
    vector_store = Chroma(
        client=chroma_client,
        collection_name="obsidian_docs",
        embedding_function=embeddings
    )
else:
    vector_store = None

# 3. Lógica de Ingesta (Barra lateral)
vault_path = "/app/obsidian_vault"
st.sidebar.markdown("---")
st.sidebar.subheader("Gestión de Conocimiento")

if st.sidebar.button("🔄 Indexar Obsidian Vault"):
    if not embeddings:
        st.sidebar.error("⚠️ Falta la GOOGLE_API_KEY en tu docker-compose.yml.")
    else:
        with st.spinner("Leyendo y procesando con Gemini..."):
            try:
                loader = DirectoryLoader(vault_path, glob="**/*.md", loader_cls=TextLoader)
                documentos = loader.load()
                
                if not documentos:
                    st.sidebar.warning("No se encontraron archivos .md.")
                else:
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
                    fragmentos = text_splitter.split_documents(documentos)
                    vector_store.add_documents(fragmentos)
                    st.sidebar.success(f"✅ ¡Éxito! Se generaron {len(fragmentos)} embeddings.")
            except Exception as e:
                st.sidebar.error(f"Error en la indexación: {e}")

# 4. Interfaz de Chat (Estilo ChatGPT / Gemini) y Lógica de Triage
st.markdown("---")

# Inicializar el historial de chat en la memoria de la sesión
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Mensaje de bienvenida del asistente
    st.session_state.messages.append({
        "role": "assistant",
        "content": "👋 ¡Hola! Soy Codex. Pega aquí el ticket de soporte y revisaré si ya lo hemos resuelto antes en Obsidian."
    })

# Mostrar el historial de mensajes en pantalla
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capturar el nuevo mensaje del usuario (El Ticket o la respuesta)
if prompt_usuario := st.chat_input("Escribe el ticket o tu mensaje aquí..."):

    # 1. Mostrar y guardar el mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt_usuario})
    with st.chat_message("user"):
        st.markdown(prompt_usuario)

    # 2. Lógica de Triage y Respuesta de la IA
    with st.chat_message("assistant"):
        if not vector_store:
            st.error("La base de datos no está lista. Revisa tu conexión y API Key.")
        else:
            with st.spinner("Analizando..."):
                try:
                    # Inicializamos el Cerebro (Gemini) para ambas rutas
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-3-flash-preview",
                        google_api_key=google_api_key,
                        temperature=0.2,
                        convert_system_message_to_human=True
                    )

                    # --- LÓGICA DE TRIAGE ---
                    # Verificamos si es el primer mensaje del usuario (El Ticket inicial)
                    if len(st.session_state.messages) == 2: # 1 bot + 1 usuario

                        # Buscamos en ChromaDB evaluando la distancia (score)
                        # ChromaDB con L2 distance: Menor score = mayor similitud.
                        resultados = vector_store.similarity_search_with_score(prompt_usuario, k=3)

                        # Evaluamos el documento más parecido (el índice 0)
                        if resultados:
                            mejor_doc, mejor_score = resultados[0]
                            # Umbral de similitud (ajustable): Cuanto más bajo, más exigente.
                            # Para L2, un score < 0.5 suele ser muy similar.
                            es_conocido = mejor_score < 0.6
                        else:
                            es_conocido = False

                        if es_conocido:
                            # RUTA A: Problema Conocido (RAG)
                            contexto = "\n\n".join([doc.page_content for doc, _ in resultados])

                            system_prompt = (
                                "Eres un asistente de soporte técnico experto. "
                                "Usa los siguientes fragmentos de contexto de Obsidian para resolver el ticket.\n"
                                "Explica la solución claramente y cita el nombre del archivo al final.\n\n"
                                f"Contexto recuperado:\n{contexto}"
                            )

                            prompt_rag = ChatPromptTemplate.from_messages([
                                ("system", system_prompt),
                                ("human", "{input}"),
                            ])

                            cadena = prompt_rag | llm
                            respuesta_ia = cadena.invoke({"input": prompt_usuario}).content

                        else:
                            # RUTA B: Problema Nuevo (Chat Libre / Inicio de MCP en el futuro)
                            system_prompt = (
                                "Eres un asistente de soporte técnico avanzado. "
                                "El agente acaba de introducir un ticket que NO está en la base de datos de conocimiento. "
                                "Admite que parece un problema nuevo y empieza a guiar al agente paso a paso para hacer debug o pedir más información (logs, configuraciones)."
                            )

                            prompt_libre = ChatPromptTemplate.from_messages([
                                ("system", system_prompt),
                                ("human", "{input}"),
                            ])

                            cadena = prompt_libre | llm
                            respuesta_ia = cadena.invoke({"input": prompt_usuario}).content

                    else:
                        # RUTA C: Conversación en curso
                        # Si ya pasamos el primer mensaje, continuamos el chat libremente.
                        # Aquí le pasamos todo el historial para que tenga memoria.
                        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

                        mensajes_langchain = [
                            SystemMessage(content="Eres un asistente de soporte técnico. Continúa ayudando al agente a resolver el problema.")
                        ]

                        # Convertimos el historial de Streamlit al formato de LangChain
                        for msg in st.session_state.messages[1:-1]: # Omitimos el primero (saludo) y el último (ya está en el input)
                            if msg["role"] == "user":
                                mensajes_langchain.append(HumanMessage(content=msg["content"]))
                            elif msg["role"] == "assistant":
                                mensajes_langchain.append(AIMessage(content=msg["content"]))

                        mensajes_langchain.append(HumanMessage(content=prompt_usuario))

                        respuesta_ia = llm.invoke(mensajes_langchain).content

                    # 3. Mostrar y guardar la respuesta
                    st.markdown(respuesta_ia)
                    st.session_state.messages.append({"role": "assistant", "content": respuesta_ia})

                except Exception as e:
                    st.error(f"Error de procesamiento: {e}")
