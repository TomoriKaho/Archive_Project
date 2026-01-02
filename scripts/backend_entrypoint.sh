#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

"${SCRIPT_DIR}/wait_for_services.sh"

if [ -f /app/alembic.ini ] && [ -d /app/migrations/versions ]; then
  echo "[backend_entrypoint] Running alembic migrations..."
  alembic upgrade head
else
  echo "[backend_entrypoint] alembic.ini or migrations/versions not found, skipping migrations."
fi

BACKEND_PORT=${BACKEND_PORT:-18000}

exec uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
