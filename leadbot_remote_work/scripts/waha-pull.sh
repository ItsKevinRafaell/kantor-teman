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
MIN_FREE_KB="${WAHA_MIN_FREE_KB:-5242880}"
FREE_KB="$(df -Pk /var/lib/docker 2>/dev/null | awk 'NR==2 {print $4}')"

if [ -z "$FREE_KB" ]; then
  FREE_KB="$(df -Pk / | awk 'NR==2 {print $4}')"
fi

if [ "$FREE_KB" -lt "$MIN_FREE_KB" ]; then
  echo "Free disk kurang untuk pull $IMAGE: ${FREE_KB}KB. Minimal disarankan ${MIN_FREE_KB}KB." >&2
  exit 3
fi

docker pull "$IMAGE"
