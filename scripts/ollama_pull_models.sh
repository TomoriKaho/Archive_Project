#!/usr/bin/env sh
set -eu

MODELS_RAW=${OLLAMA_MODELS:-}
if [ -z "$MODELS_RAW" ]; then
  MODELS_RAW=${OLLAMA_EMBED_MODEL:-}
fi
if [ -z "$MODELS_RAW" ]; then
  echo "[ollama_pull_models] OLLAMA_MODELS and OLLAMA_EMBED_MODEL are empty; skipping model pull."
  exit 0
fi

IFS=','
for model in $MODELS_RAW; do
  model=$(echo "$model" | xargs)
  if [ -z "$model" ]; then
    continue
  fi
  echo "[ollama_pull_models] Pulling model: $model"
  ollama pull "$model" || {
    echo "[ollama_pull_models] WARN: Failed to pull $model."
  }
done
