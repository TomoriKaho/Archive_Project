#!/usr/bin/env sh
set -eu

QDRANT_URL=${QDRANT_URL:-http://qdrant:6333}
QDRANT_COLLECTION=${QDRANT_COLLECTION:-Archive_Project_Collection}
QDRANT_VECTOR_SIZE=${QDRANT_VECTOR_SIZE:-}
MAX_RETRIES=${MAX_RETRIES:-60}
SLEEP_SECONDS=${SLEEP_SECONDS:-2}

log() {
  echo "[qdrant_init] $*"
}

require_vector_size() {
  if [ -z "$QDRANT_VECTOR_SIZE" ]; then
    log "QDRANT_VECTOR_SIZE is not set; unable to create collection."
    exit 1
  fi
  if ! echo "$QDRANT_VECTOR_SIZE" | grep -Eq '^[0-9]+$'; then
    log "QDRANT_VECTOR_SIZE must be a positive integer."
    exit 1
  fi
  if [ "$QDRANT_VECTOR_SIZE" -le 0 ]; then
    log "QDRANT_VECTOR_SIZE must be greater than zero."
    exit 1
  fi
}

wait_for_qdrant() {
  attempt=1
  health_url="${QDRANT_URL%/}/healthz"
  while ! curl -fsS "$health_url" >/dev/null 2>&1; do
    if [ "$attempt" -ge "$MAX_RETRIES" ]; then
      log "Qdrant not ready after ${MAX_RETRIES} attempts."
      exit 1
    fi
    log "Waiting for Qdrant at ${health_url} (attempt ${attempt}/${MAX_RETRIES})..."
    attempt=$((attempt + 1))
    sleep "$SLEEP_SECONDS"
  done
  log "Qdrant is ready."
}

collection_status() {
  curl -s -o /dev/null -w "%{http_code}" "${QDRANT_URL%/}/collections/${QDRANT_COLLECTION}"
}

create_collection() {
  payload=$(cat <<EOF
{
  "vectors": {
    "size": ${QDRANT_VECTOR_SIZE},
    "distance": "Cosine"
  }
}
EOF
)
  curl -fsS -o /dev/null \
    -X PUT \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "${QDRANT_URL%/}/collections/${QDRANT_COLLECTION}"
}

main() {
  require_vector_size
  wait_for_qdrant

  status=$(collection_status)
  if [ "$status" -eq 200 ]; then
    log "Collection ${QDRANT_COLLECTION} already exists."
    return 0
  fi
  if [ "$status" -ne 404 ]; then
    log "Unexpected status ${status} when checking collection ${QDRANT_COLLECTION}."
    exit 1
  fi

  log "Creating collection ${QDRANT_COLLECTION} with vector size ${QDRANT_VECTOR_SIZE}."
  create_collection
  log "Collection ${QDRANT_COLLECTION} created."
}

main "$@"
