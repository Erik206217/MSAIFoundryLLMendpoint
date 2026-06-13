# Execution Plan (Current Iteration)

## Scope (1-2 days)
Implement project-based chatbot + RAG while preserving current 5-model setup.

## Acceptance Criteria
- Multi-model switching works for all 5 models.
- Web search toggle works for supported models.
- Project can be created and selected.
- Session history persists after refresh/reopen.
- Files can be uploaded to project knowledge base.
- Uploaded project knowledge is used in answers.

## Step-by-Step Plan
1. Stabilize runtime config
- Use env vars for endpoints/container names.
- Keep Managed Identity token flow stable.

2. Project/session persistence
- Persist projects/sessions/messages in Cosmos.
- Ensure refresh does not lose current history.

3. Project knowledge base
- Add per-project upload and chunk storage.
- Add retrieval for prompt grounding.

4. Model and web search compatibility
- Keep existing 5 model names and routing.
- Preserve web-search agent flow for mapped models.

5. Observability baseline
- Save model, web_search flag, and token estimate per assistant turn.

6. Deploy and verify
- Build image and deploy to Container App.
- Run acceptance test checklist.

## Risks and Mitigations
- Token estimate is approximate now.
  - Mitigation: add exact token accounting from API responses in next iteration.
- Cosmos query/partition mismatch risk.
  - Mitigation: keep partition-aware queries and test with multiple projects/sessions.
- Web search depends on agent mapping names.
  - Mitigation: validate each mapped model once after deployment.

## Next Iteration (after this plan)
- True usage analytics dashboard (per project/model/day).
- Better RAG ranking and citation display.
- Image upload and OCR/vision path.
- Optional voice input (likely moderate refactor; call out before implementation).
