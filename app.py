import io
import os
import re
import uuid
from datetime import datetime

import pypdf
import requests
import streamlit as st
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import ManagedIdentityCredential, get_bearer_token_provider
from openai import AzureOpenAI


AZURE_ENDPOINT = os.getenv(
    "AZURE_ENDPOINT",
    "https://wzhe-1chatbot-resource--resource.cognitiveservices.azure.com/",
)
PROJECT_ENDPOINT = os.getenv(
    "PROJECT_ENDPOINT",
    "https://wzhe-1chatbot-resource--resource.services.ai.azure.com/api/projects/wzhe-1chatbot-resource-20260505",
)
COSMOS_ENDPOINT = os.getenv(
    "COSMOS_ENDPOINT", "https://chatbot-cosmos-wzhe.documents.azure.com:443/"
)
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME", "chatbotdb")
COSMOS_SESSIONS_CONTAINER = os.getenv("COSMOS_SESSIONS_CONTAINER", "sessions")
COSMOS_MESSAGES_CONTAINER = os.getenv("COSMOS_MESSAGES_CONTAINER", "messages")
COSMOS_DOCS_CONTAINER = os.getenv("COSMOS_DOCS_CONTAINER", "project_docs")
MAIN_API_VERSION = os.getenv("MAIN_API_VERSION", "2025-01-01-preview")
AGENT_API_VERSION = os.getenv("AGENT_API_VERSION", "2025-05-15-preview")

RESPONSES_MODELS = ["gpt-5.4", "gpt-5.4-pro"]
CHAT_MODELS = ["DeepSeek-V4-Pro", "DeepSeek-R1-0528", "grok-4-20-reasoning"]
MODEL_OPTIONS = RESPONSES_MODELS + CHAT_MODELS

AGENT_MAP = {
    "gpt-5.4": "agentgpt54forgrounding",
    "gpt-5.4-pro": "agentgpt54proforgrouding",
    "grok-4-20-reasoning": "agentgrokforgrounding",
    "DeepSeek-V4-Pro": "agentforbingsearchgrouding",
}


@st.cache_resource
def get_client() -> AzureOpenAI:
    credential = ManagedIdentityCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=MAIN_API_VERSION,
    )


@st.cache_resource
def get_cosmos_client() -> CosmosClient:
    credential = ManagedIdentityCredential()
    return CosmosClient(COSMOS_ENDPOINT, credential=credential)


def get_db():
    return get_cosmos_client().get_database_client(COSMOS_DB_NAME)


def get_sessions_container():
    return get_db().get_container_client(COSMOS_SESSIONS_CONTAINER)


def get_messages_container():
    return get_db().get_container_client(COSMOS_MESSAGES_CONTAINER)


def get_docs_container():
    # Create once if missing. This keeps architecture minimal and avoids
    # introducing an extra service only for small project-level RAG storage.
    return get_db().create_container_if_not_exists(
        id=COSMOS_DOCS_CONTAINER,
        partition_key=PartitionKey(path="/project_id"),
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = pypdf.PdfReader(io.BytesIO(uploaded_file.read()))
        pages = [page.extract_text() or "" for page in reader.pages]
        return clean_text("\n\n".join(pages))
    return clean_text(uploaded_file.read().decode("utf-8", errors="ignore"))


def split_chunks(text: str, chunk_size: int = 1000, overlap: int = 200):
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = max(end - overlap, end)
    return chunks


def load_projects():
    try:
        items = list(
            get_sessions_container().query_items(
                query="SELECT DISTINCT c.project_id, c.project_name FROM c",
                enable_cross_partition_query=True,
            )
        )
        seen = {}
        for item in items:
            seen[item["project_id"]] = item["project_name"]
        return seen
    except Exception:
        return {}


def load_sessions(project_id: str):
    try:
        return list(
            get_sessions_container().query_items(
                query="SELECT * FROM c WHERE c.project_id = @project_id ORDER BY c.created_at DESC",
                parameters=[{"name": "@project_id", "value": project_id}],
                partition_key=project_id,
            )
        )
    except Exception:
        return []


def create_session(project_id: str, project_name: str, session_name: str):
    session_id = str(uuid.uuid4())
    get_sessions_container().create_item(
        {
            "id": session_id,
            "session_id": session_id,
            "project_id": project_id,
            "project_name": project_name,
            "session_name": session_name,
            "created_at": datetime.utcnow().isoformat(),
        }
    )
    return session_id


def load_messages(session_id: str):
    try:
        items = list(
            get_messages_container().query_items(
                query="SELECT * FROM c WHERE c.session_id = @session_id ORDER BY c.created_at ASC",
                parameters=[{"name": "@session_id", "value": session_id}],
                partition_key=session_id,
            )
        )
        return items
    except Exception:
        return []


def save_message(
    session_id: str,
    role: str,
    content: str,
    model: str = "",
    web_search: bool = False,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
):
    get_messages_container().create_item(
        {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": role,
            "content": content,
            "model": model,
            "web_search": web_search,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "created_at": datetime.utcnow().isoformat(),
        }
    )


def upload_docs_to_project(project_id: str, files):
    container = get_docs_container()
    inserted = 0
    for file in files:
        text = extract_text(file)
        if not text:
            continue
        for chunk in split_chunks(text):
            container.create_item(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "file_name": file.name,
                    "content": chunk,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            inserted += 1
    return inserted


def get_project_doc_count(project_id: str) -> int:
    try:
        rows = list(
            get_docs_container().query_items(
                query="SELECT VALUE COUNT(1) FROM c WHERE c.project_id = @project_id",
                parameters=[{"name": "@project_id", "value": project_id}],
                partition_key=project_id,
            )
        )
        return int(rows[0]) if rows else 0
    except Exception:
        return 0


def retrieve_project_context(project_id: str, query_text: str, top_k: int = 4) -> str:
    try:
        docs = list(
            get_docs_container().query_items(
                query="SELECT TOP 60 c.file_name, c.content FROM c WHERE c.project_id = @project_id",
                parameters=[{"name": "@project_id", "value": project_id}],
                partition_key=project_id,
            )
        )
    except Exception:
        return ""

    if not docs:
        return ""

    query_terms = {
        term for term in re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", query_text.lower()) if len(term) > 1
    }

    scored = []
    for doc in docs:
        content = doc.get("content", "")
        content_l = content.lower()
        score = 0
        for term in query_terms:
            if term in content_l:
                score += 1
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_docs = [doc for _, doc in scored[:top_k]]
    if not top_docs:
        top_docs = docs[: min(top_k, len(docs))]

    blocks = []
    for doc in top_docs:
        blocks.append(f"[{doc.get('file_name', 'unknown')}]\n{doc.get('content', '')[:1200]}")
    return "\n\n".join(blocks)


def get_agent_token() -> str:
    credential = ManagedIdentityCredential()
    token = credential.get_token("https://ai.azure.com/.default")
    return token.token


def call_agent_responses(prompt: str, agent_name: str) -> str:
    token = get_agent_token()
    url = f"{PROJECT_ENDPOINT}/agents/{agent_name}/endpoint/protocols/openai/responses?api-version={AGENT_API_VERSION}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={"input": prompt}, timeout=90)
    response.raise_for_status()
    data = response.json()
    if "output_text" in data:
        return data["output_text"]
    for item in data.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return part.get("text", "")
    return str(data)


client = get_client()

if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "current_project_name" not in st.session_state:
    st.session_state.current_project_name = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

st.set_page_config(page_title="Max Chatbot Workspace", layout="wide")
st.markdown(
    """
<style>
html, body, [class*="css"] {
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
}
h1, h2, h3 {
  letter-spacing: -0.01em;
}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Workspace")
    selected_model = st.selectbox("Model", MODEL_OPTIONS)
    web_search = st.toggle("Web Search (Bing Agent)", value=False)

    st.divider()
    st.subheader("Projects")
    projects = load_projects()

    with st.expander("Create Project"):
        new_project_name = st.text_input("Project name", key="new_project_name")
        if st.button("Create project") and new_project_name.strip():
            st.session_state.current_project_id = str(uuid.uuid4())
            st.session_state.current_project_name = new_project_name.strip()
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.rerun()

    for project_id, project_name in projects.items():
        if st.button(f"{project_name}", key=f"project_{project_id}"):
            st.session_state.current_project_id = project_id
            st.session_state.current_project_name = project_name
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.rerun()

    if st.session_state.current_project_id:
        st.divider()
        st.subheader(f"Project: {st.session_state.current_project_name}")
        doc_count = get_project_doc_count(st.session_state.current_project_id)
        st.caption(f"Knowledge chunks: {doc_count}")

        files = st.file_uploader(
            "Upload docs to this project",
            type=["pdf", "txt", "md"],
            accept_multiple_files=True,
            key="project_docs_upload",
        )
        if st.button("Build/Update knowledge base") and files:
            with st.spinner("Indexing project documents..."):
                chunks = upload_docs_to_project(st.session_state.current_project_id, files)
            st.success(f"Indexed {chunks} chunks")

        with st.expander("Create Session"):
            new_session_name = st.text_input("Session name", key="new_session_name")
            if st.button("Create session") and new_session_name.strip():
                sid = create_session(
                    st.session_state.current_project_id,
                    st.session_state.current_project_name,
                    new_session_name.strip(),
                )
                st.session_state.current_session_id = sid
                st.session_state.messages = []
                st.rerun()

        sessions = load_sessions(st.session_state.current_project_id)
        for sess in sessions:
            if st.button(f"{sess['session_name']}", key=f"session_{sess['session_id']}"):
                st.session_state.current_session_id = sess["session_id"]
                st.session_state.messages = load_messages(sess["session_id"])
                st.rerun()

st.title("Max Chatbot Workspace")
st.caption("Project-level chat + RAG + web search (Managed Identity only)")

if not st.session_state.current_session_id:
    st.info("Create/select a project first, then create a session.")
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant" and msg.get("total_tokens", 0):
                st.caption(
                    f"model={msg.get('model', '')} | tokens={msg.get('total_tokens', 0)} "
                    f"(prompt={msg.get('prompt_tokens', 0)}, completion={msg.get('completion_tokens', 0)})"
                )

    if prompt := st.chat_input("Ask Max..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message(st.session_state.current_session_id, "user", prompt, selected_model, web_search)

        project_context = retrieve_project_context(st.session_state.current_project_id, prompt, top_k=4)
        system_prompt = "You are a helpful AI assistant for project-based work."
        if project_context:
            system_prompt += (
                "\nUse the project knowledge below as the primary reference when relevant.\n\n"
                + project_context
            )

        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            try:
                if web_search and selected_model in AGENT_MAP:
                    agent_name = AGENT_MAP[selected_model]
                    with st.spinner("Searching the web..."):
                        reply = call_agent_responses(prompt, agent_name)
                    st.write(reply)
                else:
                    messages_to_send = [{"role": "system", "content": system_prompt}]
                    for m in st.session_state.messages:
                        messages_to_send.append({"role": m["role"], "content": m["content"]})

                    if selected_model in RESPONSES_MODELS:
                        response = client.responses.create(
                            model=selected_model,
                            input=messages_to_send,
                        )
                        reply = response.output_text
                    else:
                        response = client.chat.completions.create(
                            model=selected_model,
                            messages=messages_to_send,
                        )
                        reply = response.choices[0].message.content or ""

                    st.write(reply)

                prompt_tokens = estimate_tokens(prompt + project_context)
                completion_tokens = estimate_tokens(reply)
                st.caption(
                    f"model={selected_model} | estimated tokens={prompt_tokens + completion_tokens} "
                    f"(prompt~{prompt_tokens}, completion~{completion_tokens})"
                )

                save_message(
                    st.session_state.current_session_id,
                    "assistant",
                    reply,
                    model=selected_model,
                    web_search=web_search,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": reply,
                        "model": selected_model,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    }
                )
            except Exception as exc:
                st.error(f"Error: {exc}")
