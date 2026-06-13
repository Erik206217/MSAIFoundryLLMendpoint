#!/usr/bin/env bash
set -euo pipefail

# Verifies app health and scans recent logs for Cosmos 403 firewall errors.
# Usage:
#   bash ops/verify_network.sh
# Optional overrides:
#   RG=Chatbot-rg APP=chatbotformax

RG="${RG:-Chatbot-rg}"
APP="${APP:-chatbotformax}"

echo "== Verify network/app health =="

URL="$(az containerapp show -n "${APP}" -g "${RG}" --query "properties.configuration.ingress.fqdn" -o tsv)"
if [[ -z "${URL}" ]]; then
  echo "FAIL: no ingress URL."
  exit 1
fi

TARGET="https://${URL}"
CODE="$(curl -sS -o /tmp/max_verify.html -w "%{http_code}" "${TARGET}" || true)"
echo "App URL: ${TARGET}"
echo "HTTP: ${CODE}"

LATEST_REV="$(az containerapp show -n "${APP}" -g "${RG}" --query "properties.latestRevisionName" -o tsv)"
echo "Latest revision: ${LATEST_REV}"

LOG_FILE="/tmp/${APP}_latest_logs.txt"
az containerapp logs show -n "${APP}" -g "${RG}" --revision "${LATEST_REV}" --tail 200 > "${LOG_FILE}" || true

if grep -Eiq "CosmosHttpResponseError|forbidden|cosmos.*firewall|12354d" "${LOG_FILE}"; then
  echo "WARN: Found possible Cosmos firewall errors in recent logs."
  echo "Open file: ${LOG_FILE}"
  exit 2
fi

echo "PASS: No obvious Cosmos firewall error in recent logs."
