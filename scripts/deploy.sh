#!/usr/bin/env bash
# Deploy custom_components/sinilink_udp/ to a HAOS instance over SSH and
# restart HA core. Requires the "Advanced SSH & Web Terminal" addon
# (Protection mode OFF so the `ha` CLI is available).
#
# Configuration is read from .env in the repo root (gitignored) or from
# environment variables. Copy .env.example to .env and fill it in.
#
# Required:
#   HA_HOST   IP or hostname of the HAOS instance
# Optional:
#   HA_PORT   SSH port (default 22)
#   HA_USER   SSH user (default root)
#
# Usage:
#   ./scripts/deploy.sh
#   HA_HOST=ha.local ./scripts/deploy.sh   # one-off override

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Source .env if it exists (local dev config, gitignored).
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

: "${HA_HOST:?HA_HOST is not set. Copy .env.example to .env and fill in your HAOS address.}"
HA_PORT="${HA_PORT:-22}"
HA_USER="${HA_USER:-root}"

DEST="/config/custom_components/sinilink_udp"
SRC="${REPO_ROOT}/custom_components/sinilink_udp/"

if [[ ! -d "${SRC}" ]]; then
  echo "error: source not found at ${SRC}" >&2
  exit 1
fi

echo ">> rsync ${SRC} -> ${HA_USER}@${HA_HOST}:${DEST}/"
rsync -av --delete -e "ssh -p ${HA_PORT}" "${SRC}" "${HA_USER}@${HA_HOST}:${DEST}/"

echo ">> ha core restart"
ssh -p "${HA_PORT}" "${HA_USER}@${HA_HOST}" "ha core restart"

echo ">> done. Watch logs: ssh -p ${HA_PORT} ${HA_USER}@${HA_HOST} 'ha core logs | grep -i sinilink'"
