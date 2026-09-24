#!/bin/bash
set -euo pipefail

readonly TARGET="${TARGET:-http://web:8080/Albert}"
readonly NETWORK="${NETWORK:-nanolink_back}"
readonly DURATION_SECONDS="${DURATION_SECONDS:-30}"
readonly LOAD_IMAGE="nanolink/bench:autocannon-8.0.0"

build_load_image() {
  docker build --quiet --tag "$LOAD_IMAGE" - >/dev/null <<'DOCKERFILE'
FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1
RUN npm install --global --no-fund --no-audit autocannon@8.0.0
USER node
ENTRYPOINT ["autocannon"]
DOCKERFILE
}

load() {
  docker run --rm --network "$NETWORK" "$LOAD_IMAGE" --json --connections "$1" --duration "$2" "$TARGET"
}

summary_row() {
  jq -r --arg c "$1" '"| \($c) | \(.requests.total) | \(.requests.average | round) | \(.latency.p50) ms | \(.latency.p90) ms | \(.latency.p99) ms | \(.latency.max) ms | \(.non2xx) | \(.errors + .timeouts) |"'
}

build_load_image
load 10 5 >/dev/null
echo "| Connections | Requests | Req/s | p50 | p90 | p99 | max | 3xx/4xx/5xx | errors |"
echo "|---|---|---|---|---|---|---|---|---|"
for connections in 1 10 50 100; do
  load "$connections" "$DURATION_SECONDS" | summary_row "$connections"
done
