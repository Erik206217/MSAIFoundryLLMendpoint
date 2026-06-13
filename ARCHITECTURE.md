# Architecture Contract

## 1. System Scope
This project builds a project-based enterprise chatbot + RAG system on Azure.
Core requirements:
- Managed Identity (Entra ID) only for runtime auth
- Cosmos DB persistence
- Project-level knowledge isolation
- Optional internet grounding via agent route
- Keep existing five model deployments

## 2. Runtime Topology
- UI/App Layer: Streamlit app (`app.py`)
- LLM Layer: Azure OpenAI endpoint (Responses + Chat Completions)
- Web Grounding Layer: Azure AI Foundry project agents (Bing grounding)
- Data Layer: Cosmos DB (`chatbotdb`)
- Deployment: Azure Container Apps + ACR

## 3. Auth and Security Contract
- Runtime must authenticate with `ManagedIdentityCredential`.
- Do not require API key in runtime path.
- Endpoints, DB/container names, and API versions must be configurable via env vars.
- Secrets must not be hardcoded in source.

## 4. Data Contract (Cosmos)

### 4.1 Sessions Container
Container: `sessions` (default)
Partition key assumption: `project_id`

Fields:
- `id` (session id)
- `session_id`
- `project_id`
- `project_name`
- `session_name`
- `created_at`

### 4.2 Messages Container
Container: `messages` (default)
Partition key assumption: `session_id`

Fields:
- `id`
- `session_id`
- `role` (`user` or `assistant`)
- `content`
- `model`
- `web_search` (bool)
- `prompt_tokens` (estimated for now)
- `completion_tokens` (estimated for now)
- `total_tokens`
- `created_at`

### 4.3 Project Docs Container
Container: `project_docs` (default; auto-create if missing)
Partition key: `project_id`

Fields:
- `id`
- `project_id`
- `file_name`
- `content` (chunk)
- `created_at`

## 5. Request Flow Contract

### 5.1 Non-Web Path
1. User sends message in selected project/session.
2. System retrieves project chunks from `project_docs`.
3. System constructs prompt with retrieved context.
4. System calls model route:
- Responses API for `gpt-5.4`, `gpt-5.4-pro`
- Chat Completions for other mapped chat models
5. System saves assistant reply + usage estimates to `messages`.

### 5.2 Web Grounding Path
1. If web toggle enabled and model exists in `AGENT_MAP`, call agent endpoint.
2. Return grounded output text.
3. Save output with model and usage estimates.

## 6. Model Routing Contract
Current preserved models:
- `gpt-5.4`
- `gpt-5.4-pro`
- `DeepSeek-V4-Pro`
- `DeepSeek-R1-0528`
- `grok-4-20-reasoning`

Web grounding availability depends on `AGENT_MAP` coverage.

## 7. RAG Contract (Current Phase)
- Supported upload types: `pdf`, `txt`, `md`
- Parsing:
- PDF via `pypdf`
- Text/MD via UTF-8 decode with ignore fallback
- Chunking: fixed-size character windows with overlap
- Retrieval: lightweight lexical scoring over project-scoped chunks

Note: This is baseline RAG for speed of delivery; vector retrieval can be introduced later without breaking the project/session contract.

## 8. Observability Contract (Current Phase)
- Persist model and token estimates per assistant turn in Cosmos.
- Keep deploy and diagnostics scripts under `ops/`.
- Use `ops/cloudshell_collect.sh` for environment and revision snapshots.

## 9. Performance and UX Contract
- Prioritize responsive UI and predictable output over heavy orchestration.
- Keep default prompt and retrieval sizes bounded to reduce latency.
- Prefer incremental improvements (streaming, async retrieval, caching) per iteration.

## 10. Deployment Contract
- Build image via ACR.
- Deploy by immutable tag plus update `latest`.
- Apply Container App revision suffix per release (`v36`, `v37`, etc.).
- Rollback by switching to previous revision/image tag.

## 11. Future Extension Points (Planned)
- True token usage from API usage fields (replace estimation)
- Image upload + OCR/vision RAG path
- Voice input (requires UX and API flow change)
- Backend API extraction (`backend/`) so UI calls API instead of direct data/service calls
