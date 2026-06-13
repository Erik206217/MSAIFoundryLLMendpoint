#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash ops/cloudshell_collect.sh
# Optional env overrides:
#   RG=Chatbot-rg APP=chatbotformax ACR=ca379bc9774eacr REPO=chatbotformax OUT_DIR=ops/out

RG="${RG:-Chatbot-rg}"
APP="${APP:-chatbotformax}"
ACR="${ACR:-ca379bc9774eacr}"
REPO="${REPO:-chatbotformax}"
OUT_DIR="${OUT_DIR:-ops/out}"

TS="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="${OUT_DIR}/${TS}"
mkdir -p "${RUN_DIR}"

echo "Collecting diagnostics to: ${RUN_DIR}"

az account show > "${RUN_DIR}/account.json"
az containerapp show -n "${APP}" -g "${RG}" > "${RUN_DIR}/containerapp_show.json"
az containerapp revision list -n "${APP}" -g "${RG}" > "${RUN_DIR}/revisions.json"
az containerapp replica list -n "${APP}" -g "${RG}" > "${RUN_DIR}/replicas.json"
az acr repository list -n "${ACR}" > "${RUN_DIR}/acr_repos.json"
az acr repository show-tags -n "${ACR}" --repository "${REPO}" --orderby time_desc > "${RUN_DIR}/acr_tags.json"

LATEST_REVISION="$(az containerapp show -n "${APP}" -g "${RG}" --query properties.latestRevisionName -o tsv)"
echo "${LATEST_REVISION}" > "${RUN_DIR}/latest_revision.txt"

az containerapp logs show -n "${APP}" -g "${RG}" --revision "${LATEST_REVISION}" --tail 200 > "${RUN_DIR}/logs_latest_revision.txt" || true
az containerapp show -n "${APP}" -g "${RG}" --query "properties.template.containers[0].env" -o json > "${RUN_DIR}/env.json"

# App source snapshots from running container (best effort)
az containerapp exec -n "${APP}" -g "${RG}" --command "cat /app/app.py" > "${RUN_DIR}/container_app.py" || true
az containerapp exec -n "${APP}" -g "${RG}" --command "cat /app/requirements.txt" > "${RUN_DIR}/container_requirements.txt" || true

cat > "${RUN_DIR}/SUMMARY.txt" <<EOF
Collected at: ${TS}
Resource Group: ${RG}
Container App: ${APP}
Latest Revision: ${LATEST_REVISION}
ACR: ${ACR}
Repository: ${REPO}
EOF

echo
echo "Done."
echo "Open folder: ${RUN_DIR}"
echo "Most useful files:"
echo "  - ${RUN_DIR}/SUMMARY.txt"
echo "  - ${RUN_DIR}/containerapp_show.json"
echo "  - ${RUN_DIR}/revisions.json"
echo "  - ${RUN_DIR}/logs_latest_revision.txt"
