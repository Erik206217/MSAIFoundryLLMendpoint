# PRD - Max Chatbot (Phase 1)

## 1. Product Summary
Build a project-oriented chatbot + RAG workspace for internal use.
Users should be able to:
- create projects
- create sessions per project
- upload project-specific files
- chat with five existing model deployments
- optionally use web grounding
- retain history after refresh

This phase prioritizes reliable baseline capability over full enterprise feature depth.

## 2. Goals
- Deliver project-level isolation for chat and knowledge.
- Preserve existing model investment (five deployments).
- Run with Managed Identity in Azure runtime.
- Provide minimal but useful observability (model + token estimate persistence).

## 3. Non-Goals (Phase 1)
- Full RBAC user system
- Complex multi-tenant admin console
- Voice input pipeline
- Image-native RAG
- Advanced analytics dashboards

## 4. Target Users
- Internal operators and business users who need project-specific AI assistance.
- User skill level includes non-coding users.

## 5. Core User Stories
1. As a user, I can create and select a project.
2. As a user, I can create multiple sessions under a project.
3. As a user, I can upload files to a project knowledge base.
4. As a user, I can ask questions and receive answers based on project docs.
5. As a user, I can switch among five model deployments.
6. As a user, I can toggle web grounding for supported models.
7. As a user, I can refresh and still see session history.

## 6. Functional Requirements

### FR-1 Project Management
- Create project (name)
- Select project from existing list

### FR-2 Session Management
- Create session under selected project
- Load existing sessions for selected project

### FR-3 Messaging Persistence
- Save each user and assistant message in Cosmos
- Load full session conversation in chronological order

### FR-4 Knowledge Upload and Retrieval
- Accept `pdf/txt/md` uploads
- Parse and chunk content
- Save chunks in project-scoped store
- Retrieve top relevant chunks for prompt grounding

### FR-5 Model and Web Routing
- Keep five current models selectable
- Route supported models to Responses API / Chat Completions accordingly
- If web toggle enabled and model is mapped, call agent grounding endpoint

### FR-6 Usage Metadata
- Save model name and token estimate fields per assistant turn

## 7. Non-Functional Requirements
- Authentication: Managed Identity only in runtime
- Availability: app should remain usable across refresh and restarts
- Latency: prioritize perceived responsiveness and bounded context size
- Maintainability: env-driven config, small incremental changes

## 8. Constraints
- Do not break current Azure Container Apps deployment path
- Do not remove existing 5 model deployments
- Keep architecture simple for rapid iteration

## 9. Acceptance Criteria (Phase 1 Exit)
- [ ] User can create project and session in UI
- [ ] User can upload docs to selected project
- [ ] User can ask doc-related question and get grounded answer
- [ ] All five models can be selected and produce responses
- [ ] Web toggle works for mapped models
- [ ] Refresh preserves message history from Cosmos
- [ ] Assistant turns persist model and token estimate metadata

## 10. Release Checklist
- [ ] Code merged to `main`
- [ ] Image built and tagged in ACR
- [ ] Container App updated to new revision
- [ ] Smoke tests completed on production URL

## 11. Future Iterations
- Exact token accounting and analytics dashboard
- Claude-like UI polish and information hierarchy
- Voice input (if approved as moderate refactor)
- Image upload and multimodal RAG
- Domain branding update (Max-related memorable hostname)
