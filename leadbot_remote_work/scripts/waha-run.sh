#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/leadbot}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

IMAGE="${WAHA_IMAGE:-devlikeapro/waha:noweb}"
CONTAINER_NAME="${WAHA_CONTAINER_NAME:-leadbot-waha}"
HOST_PORT="${WAHA_HOST_PORT:-3001}"
SESSION_DIR="${WAHA_SESSION_DIR:-$APP_DIR/.waha/.sessions}"
MEDIA_DIR="${WAHA_MEDIA_DIR:-$APP_DIR/.waha/.media}"
WEBHOOK_URL="${WAHA_WEBHOOK_URL:-http://host.docker.internal:3000/api/webhook}"
WEBHOOK_EVENTS="${WAHA_WEBHOOK_EVENTS:-message}"

if [ -z "${WAHA_API_KEY:-}" ]; then
  echo "WAHA_API_KEY belum diset di $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$SESSION_DIR" "$MEDIA_DIR"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image $IMAGE belum ada. Pull manual setelah storage VPS dinaikkan:" >&2
  echo "  docker pull $IMAGE" >&2
  exit 2
fi

existing="$(docker ps -aq -f name="^/${CONTAINER_NAME}$")"
if [ -n "$existing" ]; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

exec docker run --rm \
  --name "$CONTAINER_NAME" \
  --add-host=host.docker.internal:host-gateway \
  --log-driver=json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  -p "127.0.0.1:${HOST_PORT}:3000" \
  -v "$SESSION_DIR:/app/.sessions" \
  -v "$MEDIA_DIR:/app/.media" \
  -e "WHATSAPP_API_KEY=${WAHA_API_KEY}" \
  -e "WHATSAPP_DEFAULT_ENGINE=${WAHA_ENGINE:-NOWEB}" \
  -e "WHATSAPP_HOOK_URL=${WEBHOOK_URL}" \
  -e "WHATSAPP_HOOK_EVENTS=${WEBHOOK_EVENTS}" \
  -e "WHATSAPP_HOOK_CUSTOM_HEADERS=X-Waha-Secret:${WAHA_WEBHOOK_SECRET:-}" \
  -e "WAHA_LOCAL_STORE_BASE_DIR=/app/.sessions" \
  -e "WHATSAPP_FILES_FOLDER=/app/.media" \
  "$IMAGE"
