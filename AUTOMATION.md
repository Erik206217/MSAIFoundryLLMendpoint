# Automation Setup (One-Time)

This repo now has auto deployment and verification workflow:
- `.github/workflows/deploy-and-verify.yml`

## Required GitHub Secret
Create repo secret:
- `AZURE_CREDENTIALS`

Value format (service principal JSON):
```json
{
  "clientId": "<appId>",
  "clientSecret": "<password>",
  "subscriptionId": "<subscription>",
  "tenantId": "<tenant>"
}
```

## Required Azure Permissions (for that service principal)
- `AcrPush` on ACR `ca379bc9774eacr`
- `Contributor` (or scoped equivalent) on Container App resource group `Chatbot-rg`

## Behavior
- Every push to `main` triggers:
1. ACR build (`sha-<commit>`, `latest`)
2. Container App update to new image
3. Online health check (`HTTP 200`)

## Manual fallback
- Deploy: `bash ops/deploy.sh v37`
- Verify: `bash ops/verify.sh`
