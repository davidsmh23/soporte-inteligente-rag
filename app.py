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

# 4. Interfaz del Agente y Lógica RAG
st.markdown("### 📝 Ingresa el Ticket de Soporte")
ticket_text = st.text_area("Copia y pega el contenido del ticket aquí:", height=150)

if st.button("🚀 Consultar a la IA"):
    if not ticket_text:
        st.warning("Por favor, ingresa el texto del ticket.")
    elif not vector_store:
        st.error("La base de datos no está lista. Revisa tu conexión y API Key.")
    else:
        with st.spinner("Analizando la base de conocimiento y generando respuesta..."):
            try:
                # A) El Cerebro: Inicializamos el modelo de texto de Gemini
                llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", google_api_key=google_api_key, temperature=0.2, convert_system_message_to_human=True)

                # B) Las Instrucciones (System Prompt)
                system_prompt = (
                    "Eres un asistente de soporte técnico experto llamado Codex. "
                    "Usa los siguientes fragmentos de contexto recuperados de nuestra base de conocimiento (Obsidian) "
                    "para resolver el ticket del agente.\n\n"
                    "Reglas:\n"
                    "1. Si la solución está en el contexto, explícala claramente y cita el nombre del archivo al final.\n"
                    "2. Si el contexto no tiene la solución exacta, di 'Parece un problema nuevo' y sugiere pasos lógicos de debug.\n"
                    "3. Sé conciso y profesional.\n\n"
                    "Contexto recuperado:\n{context}"
                )
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}"),
                ])

                # C) La Cadena (RAG Pipeline)
                # 1. Creamos el recuperador (busca los 3 documentos más parecidos)
                retriever = vector_store.as_retriever(search_kwargs={"k": 3})
                
                # 2. Unimos el LLM con el Prompt
                question_answer_chain = create_stuff_documents_chain(llm, prompt)
                
                # 3. Unimos el Recuperador con la Cadena de Respuesta
                rag_chain = create_retrieval_chain(retriever, question_answer_chain)

                # D) ¡Ejecutamos la consulta!
                respuesta = rag_chain.invoke({"input": ticket_text})

                # Mostramos la respuesta en pantalla
                st.markdown("---")
                st.markdown("### 🤖 Respuesta de Codex:")
                st.info(respuesta["answer"])
                
                # (Opcional) Mostrar de dónde sacó la información
                with st.expander("📄 Ver fuentes utilizadas (Documentos de Obsidian)"):
                    for i, doc in enumerate(respuesta["context"]):
                        origen = doc.metadata.get("source", "Archivo desconocido")
                        st.write(f"**Fuente {i+1}:** `{origen}`")
                        
            except Exception as e:
                st.error(f"Ocurrió un error al consultar a Gemini: {e}")
