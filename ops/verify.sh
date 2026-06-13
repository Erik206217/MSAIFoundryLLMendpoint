#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash ops/verify.sh
# Optional env overrides:
#   RG=Chatbot-rg APP=chatbotformax

RG="${RG:-Chatbot-rg}"
APP="${APP:-chatbotformax}"

echo "Checking Container App status..."
az containerapp show -n "${APP}" -g "${RG}" --query "{latestRevision:properties.latestRevisionName,image:properties.template.containers[0].image,url:properties.configuration.ingress.fqdn}" -o table

URL="$(az containerapp show -n "${APP}" -g "${RG}" --query "properties.configuration.ingress.fqdn" -o tsv)"
if [[ -z "${URL}" ]]; then
  echo "No ingress URL found."
  exit 1
fi

TARGET="https://${URL}"
echo "Probing: ${TARGET}"

for i in {1..8}; do
  code="$(curl -sS -o /tmp/max_probe.html -w "%{http_code}" "${TARGET}" || true)"
  if [[ "${code}" == "200" ]]; then
    echo "PASS: HTTP 200 from app."
    exit 0
  fi
  echo "Attempt ${i}: HTTP ${code}. Retrying in 10s..."
  sleep 10
done

echo "FAIL: app did not return HTTP 200 in time."
exit 2
