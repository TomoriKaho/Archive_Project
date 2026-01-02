#!/usr/bin/env bash
set -euo pipefail

MAX_RETRIES=${MAX_RETRIES:-60}
SLEEP_SECONDS=${SLEEP_SECONDS:-2}

log() {
  echo "[wait_for_services] $*"
}

wait_for_port() {
  local name=$1
  local host=$2
  local port=$3
  local attempt=1

  while ! nc -z "$host" "$port" >/dev/null 2>&1; do
    if [ "$attempt" -ge "$MAX_RETRIES" ]; then
      log "ERROR: $name not reachable at ${host}:${port} after ${MAX_RETRIES} attempts."
      return 1
    fi
    log "Waiting for $name at ${host}:${port} (attempt ${attempt}/${MAX_RETRIES})..."
    attempt=$((attempt + 1))
    sleep "$SLEEP_SECONDS"
  done
  log "$name is reachable at ${host}:${port}."
}

wait_for_http() {
  local name=$1
  shift
  local attempt=1

  while true; do
    for url in "$@"; do
      if curl -fsS "$url" >/dev/null 2>&1; then
        log "$name is responding at ${url}."
        return 0
      fi
    done
    if [ "$attempt" -ge "$MAX_RETRIES" ]; then
      log "ERROR: $name not ready after ${MAX_RETRIES} attempts."
      return 1
    fi
    log "Waiting for $name HTTP (attempt ${attempt}/${MAX_RETRIES})..."
    attempt=$((attempt + 1))
    sleep "$SLEEP_SECONDS"
  done
}

resolve_postgres() {
  if [ -n "${POSTGRES_HOST:-}" ] && [ -n "${POSTGRES_PORT:-}" ]; then
    echo "$POSTGRES_HOST" "$POSTGRES_PORT"
    return 0
  fi
  if [ -z "${DATABASE_URL:-}" ]; then
    echo "postgres" "5432"
    return 0
  fi
  python - <<'PY'
import os
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
parsed = urlparse(url)
print(parsed.hostname or "postgres", parsed.port or 5432)
PY
}

main() {
  read -r pg_host pg_port < <(resolve_postgres)
  wait_for_port "Postgres" "$pg_host" "$pg_port"

  local qdrant_url=${QDRANT_URL:-http://qdrant:6333}
  wait_for_http "Qdrant" "${qdrant_url%/}/healthz" "${qdrant_url%/}/readyz"

  local ollama_url=${OLLAMA_BASE_URL:-${OLLAMA_URL:-http://ollama:11434}}
  wait_for_http "Ollama" "${ollama_url%/}/api/tags"
}

main "$@"
