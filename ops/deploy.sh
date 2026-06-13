#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash ops/deploy.sh v36
# Optional env overrides:
#   RG=Chatbot-rg APP=chatbotformax ACR=ca379bc9774eacr REPO=chatbotformax REPO_URL=<git-url> BRANCH=main

if [[ $# -lt 1 ]]; then
  echo "Usage: bash ops/deploy.sh <tag>"
  echo "Example: bash ops/deploy.sh v36"
  exit 1
fi

TAG="$1"
RG="${RG:-Chatbot-rg}"
APP="${APP:-chatbotformax}"
ACR="${ACR:-ca379bc9774eacr}"
REPO="${REPO:-chatbotformax}"
REPO_URL="${REPO_URL:-https://github.com/Erik206217/MSAIFoundryLLMendpoint.git}"
BRANCH="${BRANCH:-main}"

IMAGE="${ACR}.azurecr.io/${REPO}:${TAG}"
LATEST_IMAGE="${ACR}.azurecr.io/${REPO}:latest"
REV_SUFFIX="$(echo "${TAG}" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')"
if [[ -z "${REV_SUFFIX}" ]]; then
  REV_SUFFIX="deploy$(date +%H%M%S)"
fi

echo "Building image:"
echo "  ${IMAGE}"
az acr build -r "${ACR}" -t "${REPO}:${TAG}" -t "${REPO}:latest" "${REPO_URL}#${BRANCH}"

echo
echo "Updating container app revision suffix: ${REV_SUFFIX}"
az containerapp update -n "${APP}" -g "${RG}" --image "${IMAGE}" --revision-suffix "${REV_SUFFIX}" > /tmp/containerapp_update.json

echo
echo "Deployment summary:"
az containerapp show -n "${APP}" -g "${RG}" --query "{latestRevision:properties.latestRevisionName,image:properties.template.containers[0].image,url:properties.configuration.ingress.fqdn}" -o table

echo
echo "Tip: latest tag also updated to ${LATEST_IMAGE}"
