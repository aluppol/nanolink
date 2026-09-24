#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
for image in web backend redirect queue cache; do
  export "IMAGE_$(printf '%s' "$image" | tr '[:lower:]' '[:upper:]')=nanolink/${image}:dev"
done
docker compose -p nanolink-dev -f deploy/compose.yaml -f dev/compose.yaml down "$@"
