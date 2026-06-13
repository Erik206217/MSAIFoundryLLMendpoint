# Max Chatbot Program Goal

## Final Goal (North Star)
Build a stable, maintainable enterprise chatbot + RAG platform for Max with:
- Managed Identity / Entra ID only (no API key mode in runtime)
- Cosmos DB persistence
- Internet grounding/search capability
- Project-based workspace isolation
- Per-project knowledge base (document upload and retrieval)
- Observable usage (token usage and model-level traces)
- Fast and smooth response experience
- Friendly domain name (brandable, easy to remember)

## Product Direction
- UX style should move toward Claude-like clean workspace layout.
- Keep architecture simple first; scale components only when needed.
- Prefer low-risk incremental upgrades over big-bang rewrites.

## Non-Negotiable Constraints
- Do not rely on API keys in app runtime.
- Managed Identity must stay the primary auth path.
- Preserve existing 5 model deployments unless explicitly changed.
- Changes should be deployable in small increments.

## Current Priority
Deliver project-based chatbot + RAG baseline with measurable acceptance checks.
