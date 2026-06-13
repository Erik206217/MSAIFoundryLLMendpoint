import streamlit as st
from openai import AzureOpenAI
from azure.identity import ManagedIdentityCredential, get_bearer_token_provider
from azure.cosmos import CosmosClient
import pypdf
import requests
import uuid
from datetime import datetime
import os

AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://wzhe-1chatbot-resource--resource.cognitiveservices.azure.com/")
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "https://wzhe-1chatbot-resource--resource.services.ai.azure.com/api/projects/wzhe-1chatbot-resource-20260505")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://chatbot-cosmos-wzhe.documents.azure.com:443/")
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME", "chatbotdb")
COSMOS_SESSIONS_CONTAINER = os.getenv("COSMOS_SESSIONS_CONTAINER", "sessions")
COSMOS_MESSAGES_CONTAINER = os.getenv("COSMOS_MESSAGES_CONTAINER", "messages")
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
def get_client():
    credential = ManagedIdentityCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=MAIN_API_VERSION
    )

@st.cache_resource
def get_cosmos_client():
    credential = ManagedIdentityCredential()
    return CosmosClient(COSMOS_ENDPOINT, credential=credential)

def get_db():
    return get_cosmos_client().get_database_client(COSMOS_DB_NAME)

def get_sessions_container():
    return get_db().get_container_client(COSMOS_SESSIONS_CONTAINER)

def get_messages_container():
    return get_db().get_container_client(COSMOS_MESSAGES_CONTAINER)

def load_projects():
    try:
        items = list(get_sessions_container().query_items(
            query="SELECT DISTINCT c.project_id, c.project_name FROM c",
            enable_cross_partition_query=True
        ))
        seen = {}
        for item in items:
            pid = item["project_id"]
            if pid not in seen:
                seen[pid] = item["project_name"]
        return seen
    except:
        return {}

def load_sessions(project_id):
    try:
        items = list(get_sessions_container().query_items(
            query="SELECT * FROM c WHERE c.project_id = @project_id ORDER BY c.created_at DESC",
            parameters=[{"name": "@project_id", "value": project_id}],
            partition_key=project_id
        ))
        return items
    except:
        return []

def create_session(project_id, project_name, session_name):
    session_id = str(uuid.uuid4())
    get_sessions_container().create_item({
        "id": session_id,
        "session_id": session_id,
        "project_id": project_id,
        "project_name": project_name,
        "session_name": session_name,
        "created_at": datetime.utcnow().isoformat()
    })
    return session_id

def load_messages(session_id):
    try:
        items = list(get_messages_container().query_items(
            query="SELECT * FROM c WHERE c.session_id = @session_id ORDER BY c.created_at ASC",
            parameters=[{"name": "@session_id", "value": session_id}],
            partition_key=session_id
        ))
        return [{"role": m["role"], "content": m["content"]} for m in items]
    except:
        return []

def save_message(session_id, role, content):
    get_messages_container().create_item({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": role,
        "content": content,
        "created_at": datetime.utcnow().isoformat()
    })

def get_agent_token():
    credential = ManagedIdentityCredential()
    token = credential.get_token("https://ai.azure.com/.default")
    return token.token

def call_agent_responses(prompt, agent_name):
    token = get_agent_token()
    url = f"{PROJECT_ENDPOINT}/agents/{agent_name}/endpoint/protocols/openai/responses?api-version={AGENT_API_VERSION}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"input": prompt}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "output_text" in data:
        return data["output_text"]
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    return c.get("text", "")
    return str(data)

client = get_client()

missing_required_env = [
    key for key in ["AZURE_ENDPOINT", "PROJECT_ENDPOINT", "COSMOS_ENDPOINT"]
    if not os.getenv(key)
]
if missing_required_env:
    st.warning(
        "Missing environment variables: "
        + ", ".join(missing_required_env)
        + ". Using built-in defaults."
    )

if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "current_project_name" not in st.session_state:
    st.session_state.current_project_name = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

st.set_page_config(page_title="Azure 多模型智能 Chatbot", layout="wide")

with st.sidebar:
    st.header("⚙️ 设置")
    model = st.selectbox("选择模型", MODEL_OPTIONS)
    st.success(f"当前模型: {model}")
    st.divider()
    web_search = st.toggle("🌐 联网搜索", value=False)
    if web_search:
        st.info("已开启 Bing 实时联网")
    st.divider()

    st.subheader("📁 Projects")
    projects = load_projects()

    with st.expander("➕ 新建 Project"):
        new_project_name = st.text_input("Project 名称", key="new_proj")
        if st.button("创建 Project") and new_project_name:
            st.session_state.current_project_id = str(uuid.uuid4())
            st.session_state.current_project_name = new_project_name
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.rerun()

    for pid, pname in projects.items():
        if st.button(f"📁 {pname}", key=f"proj_{pid}"):
            st.session_state.current_project_id = pid
            st.session_state.current_project_name = pname
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.rerun()

    if st.session_state.current_project_id:
        st.divider()
        st.subheader(f"💬 {st.session_state.current_project_name}")

        with st.expander("➕ 新建对话"):
            new_session_name = st.text_input("对话名称", key="new_sess")
            if st.button("创建对话") and new_session_name:
                sid = create_session(
                    st.session_state.current_project_id,
                    st.session_state.current_project_name,
                    new_session_name
                )
                st.session_state.current_session_id = sid
                st.session_state.messages = []
                st.rerun()

        sessions = load_sessions(st.session_state.current_project_id)
        for sess in sessions:
            if st.button(f"💬 {sess['session_name']}", key=f"sess_{sess['session_id']}"):
                st.session_state.current_session_id = sess["session_id"]
                st.session_state.messages = load_messages(sess["session_id"])
                st.rerun()

st.title("🤖 Azure 多模型智能 Chatbot")
st.caption("纯 Azure 托管 | 支持模型切换 + 多Project + 对话历史")

if not st.session_state.current_session_id:
    st.info("👈 请先在左侧创建或选择一个 Project，然后新建对话")
else:
    system_prompt = "You are a helpful AI assistant."

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("输入消息..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message(st.session_state.current_session_id, "user", prompt)
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            try:
                if web_search and model in AGENT_MAP:
                    agent_name = AGENT_MAP[model]
                    with st.spinner("🔍 正在联网搜索..."):
                        reply = call_agent_responses(prompt, agent_name)
                    st.write(reply)
                else:
                    if web_search and model not in AGENT_MAP:
                        st.info("此模型不支持联网，已切换为直接回答")
                    messages_to_send = [{"role": "system", "content": system_prompt}] + st.session_state.messages
                    if model in RESPONSES_MODELS:
                        response = client.responses.create(
                            model=model, input=messages_to_send, stream=True
                        )
                        reply = st.write_stream(
                            chunk.delta for chunk in response
                            if hasattr(chunk, "delta") and chunk.delta
                        )
                    else:
                        response = client.chat.completions.create(
                            model=model, messages=messages_to_send, stream=True
                        )
                        reply = st.write_stream(
                            chunk.choices[0].delta.content or ""
                            for chunk in response
                            if chunk.choices
                        )
                save_message(st.session_state.current_session_id, "assistant", reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"错误: {str(e)}")
INFO: received success status from cluster
