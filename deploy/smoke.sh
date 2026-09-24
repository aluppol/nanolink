#!/bin/bash
# Proves the web gateway reaches both services and the redirect service can read MongoDB.
set -euo pipefail

http_status() {
  docker compose --env-file "$IMAGES_ENV" exec -T web wget -q -S -O /dev/null "http://127.0.0.1:8080$1" 2>&1 \
    | awk '/^ *HTTP\//{code=$2} END{print code}' || true
}

expect() {
  local actual
  actual=$(http_status "$1")
  echo "GET $1 -> ${actual} (expected $2)"
  [ "$actual" = "$2" ]
}

expect /healthz 200
expect /ping 200
expect /openapi.json 200
expect /abcdef 404
