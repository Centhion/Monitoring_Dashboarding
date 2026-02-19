#!/usr/bin/env bash
# Convenience wrapper to run docker compose from the repo root.
# Avoids typing the full -f path for every command.
#
# Usage (from repo root):
#   ./dc.sh up -d           Start the stack
#   ./dc.sh logs -f          Stream logs
#   ./dc.sh restart grafana  Restart a service
#   ./dc.sh down -v          Stop and remove volumes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/deploy/docker/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/.env"

CMD=(docker compose -f "${COMPOSE_FILE}")
if [ -f "${ENV_FILE}" ]; then
    CMD+=(--env-file "${ENV_FILE}")
fi

exec "${CMD[@]}" "$@"
