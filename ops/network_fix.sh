#!/usr/bin/env bash
set -euo pipefail

# Fast recovery for Cosmos firewall blocking Container App egress.
# Usage:
#   bash ops/network_fix.sh
# Optional overrides:
#   RG=Chatbot-rg APP=chatbotformax COSMOS=chatbot-cosmos-wzhe BLOCKED_IP=130.33.185.188 bash ops/network_fix.sh

RG="${RG:-Chatbot-rg}"
APP="${APP:-chatbotformax}"
COSMOS="${COSMOS:-chatbot-cosmos-wzhe}"
BLOCKED_IP="${BLOCKED_IP:-130.33.185.188}"

echo "== Network quick fix =="
echo "RG=${RG}"
echo "APP=${APP}"
echo "COSMOS=${COSMOS}"

echo
echo "1) Ensure Cosmos public network access is enabled (selected networks/firewall mode)"
az cosmosdb update -g "${RG}" -n "${COSMOS}" --public-network-access ENABLED 1>/dev/null

echo
echo "2) Collect possible Container App outbound IPs"
APP_IPS_RAW="$(az containerapp show -g "${RG}" -n "${APP}" --query "properties.outboundIpAddresses" -o tsv || true)"
APP_IPS_CSV="${APP_IPS_RAW// /}"

IPS=("${BLOCKED_IP}")
if [[ -n "${APP_IPS_CSV}" ]]; then
  IFS=',' read -r -a EXTRA_IPS <<< "${APP_IPS_CSV}"
  for ip in "${EXTRA_IPS[@]}"; do
    if [[ -n "${ip}" ]]; then
      IPS+=("${ip}")
    fi
  done
fi

echo "Will allow these IPs:"
printf ' - %s\n' "${IPS[@]}" | awk '!seen[$0]++'

echo
echo "3) Add Cosmos firewall rules"
printf '%s\n' "${IPS[@]}" | awk '!seen[$0]++' | while read -r ip; do
  az cosmosdb network-rule add -g "${RG}" -n "${COSMOS}" --ip-address "${ip}" 1>/dev/null || true
  echo "Added/kept: ${ip}"
done

echo
echo "4) Show current Cosmos firewall rules"
az cosmosdb show -g "${RG}" -n "${COSMOS}" --query "ipRules[].ipAddressOrRange" -o tsv || true

echo
echo "Done. Wait 1-2 minutes, then retry in app UI."
