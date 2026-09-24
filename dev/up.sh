#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

readonly IMAGES=(web backend redirect queue cache)

build_images() {
  for image in "${IMAGES[@]}"; do
    echo "building nanolink/${image}:dev"
    docker build --platform linux/amd64 --quiet --tag "nanolink/${image}:dev" "services/${image}" >/dev/null
  done
}

generate_secrets() {
  [ -f deploy/.env ] && return
  umask 077
  grep -E '^[A-Z][A-Z0-9_]*=__GENERATE__$' deploy/env.example | cut -d= -f1 | while read -r name; do
    printf '%s=%s\n' "$name" "$(openssl rand -hex 32)"
  done > deploy/.env
}

export_image_names() {
  for image in "${IMAGES[@]}"; do
    export "IMAGE_$(printf '%s' "$image" | tr '[:lower:]-' '[:upper:]_')=nanolink/${image}:dev"
  done
}

build_images
generate_secrets
export_image_names
docker network inspect nanolink_back >/dev/null 2>&1 || docker network create nanolink_back >/dev/null
docker compose -p nanolink-dev -f deploy/compose.yaml -f dev/compose.yaml up --detach --wait --pull never
echo "NanoLink runs at http://127.0.0.1:8088 — sign in as alice, bob, admin or guest"
