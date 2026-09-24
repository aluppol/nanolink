#!/bin/bash
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
backend_image="$(grep '^IMAGE_BACKEND=' "$IMAGES_ENV" | cut -d= -f2-)"

docker compose --env-file "$IMAGES_ENV" exec -T web demo-reset
docker run --rm --interactive --network nanolink_back --read-only --cap-drop ALL \
  --security-opt no-new-privileges:true "$backend_image" python - < "$here/smoke.py"
