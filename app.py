import streamlit as st
import os
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import pypdf
import io

# ==================== 配置（部署到 Azure 后用环境变量） ====================
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://<你的-resource>.openai.azure.com/openai/v1/")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")

MODEL_OPTIONS = [
    "gpt-5.4-pro",           # 推荐主力模型，综合能力强
    "DeepSeek-V4-Pro",       # 推理能力很强，适合复杂问题
    "DeepSeek-V4-Flash",     # 速度快、成本低，适合简单任务
    "gpt-image-2"            # 支持图片理解（vision 模型）
]


@st.cache_resource
def get_client():
    if AZURE_API_KEY:
        return OpenAI(base_url=AZURE_ENDPOINT, api_key=AZURE_API_KEY)
    else:
        token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")
        return OpenAI(base_url=AZURE_ENDPOINT, api_key=token_provider)

client = get_client()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "You are a helpful AI assistant. Use knowledge base when available."}]
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = ""
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

def extract_text(file):
    if file.name.lower().endswith(".pdf"):
        reader = pypdf.PdfReader(io.BytesIO(file.read()))
        return "\n\n".join([p.extract_text() or "" for p in reader.pages])
    return file.read().decode("utf-8", errors="ignore")

with st.sidebar:
    st.header("⚙️ 设置")
    selected_model = st.selectbox("🔄 选择模型 / Switch Model", MODEL_OPTIONS, index=0)
    st.success(f"当前模型: {selected_model}")

    st.divider()
    st.header("📚 知识库（上传文档）")
    files = st.file_uploader("上传 PDF/TXT（支持多文件）", type=["pdf", "txt", "md"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in [x["name"] for x in st.session_state.uploaded_files]:
                text = extract_text(f)
                st.session_state.knowledge_base += f"\n\n=== {f.name} ===\n{text}"
                st.session_state.uploaded_files.append({"name": f.name})
        st.success("知识已添加")
    
    if st.session_state.uploaded_files:
        for f in st.session_state.uploaded_files:
            st.write(f"• {f['name']}")
    
    if st.button("清空知识库"):
        st.session_state.knowledge_base = ""
        st.session_state.uploaded_files = []
        st.rerun()

st.title("🤖 Azure 多模型智能 Chatbot")
st.caption("纯 Azure 托管 | 支持模型切换 + 文档知识库")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("输入问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    full_msgs = []
    sys_prompt = st.session_state.messages[0]["content"]
    if st.session_state.knowledge_base:
        sys_prompt += f"\n\n【知识库内容】\n{st.session_state.knowledge_base}"
    full_msgs.append({"role": "system", "content": sys_prompt})
    full_msgs.extend(st.session_state.messages[1:])

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_resp = ""
        try:
            stream = client.chat.completions.create(
                model=selected_model,
                messages=full_msgs,
                stream=True,
                temperature=0.7,
                max_tokens=1200
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_resp += chunk.choices[0].delta.content
                    placeholder.markdown(full_resp + "▌")
            placeholder.markdown(full_resp)
            st.session_state.messages.append({"role": "assistant", "content": full_resp})
        except Exception as e:
            st.error(str(e))
