# NanoLink

NanoLink is a URL shortener built as a small distributed system. Link creation is asynchronous: an API gateway queues each request on NATS JetStream, a batch worker creates the links in MongoDB, and a notification service pushes the result to the browser. Clicks take a separate hot path: a Fastify redirect service reads through a Valkey cache and falls back to MongoDB when the cache is down.

Nine hardened containers, all non-root and read-only, run within a 1.25 GB memory budget. Sign-in is Keycloak (OpenID Connect) through oauth2-proxy, and the application still checks every access token itself.

- **Status:** feature-complete and tested locally (unit, integration, smoke and end-to-end). CI is configured and runs from the first push of `dev`. Deployment to `https://nanolink.luppol.com` (demo server, guest login) waits for the server side of the pipeline.
- **Source:** [github.com/aluppol/nanolink](https://github.com/aluppol/nanolink) · License: AGPL-3.0

<p>
  <img src="docs/screenshots/ui-guest.jpg" alt="NanoLink signed in as the shared guest account: sandbox banner, the shorten form and the seeded links" width="68%">
  <img src="docs/screenshots/ui-mobile.jpg" alt="NanoLink on a narrow screen: the shorten form and a user's links" width="28%">
</p>

*The UI from a local run, signed in as the guest (left) and as a user on a narrow screen (right).*

## Architecture

```mermaid
flowchart LR
    browser([Browser]) --> edge["Caddy + oauth2-proxy<br/>sign-in at auth.luppol.com"]
    edge --> web["web<br/>nginx + UI"]
    web -- "/api/*" --> gateway["gateway<br/>FastAPI"]
    web -- "/api/notifications (SSE)" --> notifier["notifier<br/>FastAPI"]
    web -- "/{code}" --> redirect["redirect<br/>Fastify"]
    gateway -- "create task" --> tasks[("JetStream<br/>LINK_TASKS")]
    tasks -- "pull, batches of 100" --> creator["creator<br/>batch worker"]
    creator -- "insert" --> mongo[("MongoDB")]
    creator -- "result" --> results[("JetStream<br/>LINK_RESULTS")]
    results --> notifier
    gateway -- "list, change, delete" --> mongo
    gateway -- "invalidate" --> cache[("Valkey")]
    redirect -- "read-through" --> cache
    redirect -- "miss or cache down" --> mongo
```

| Service | Built with | Job | Memory limit |
|---|---|---|---|
| `web` | nginx 1.29, TypeScript UI (no framework, esbuild) | the only entry point: serves the UI and routes `/api/*`, the notification stream and short codes | 32 MiB |
| `gateway` | Python 3.12, FastAPI | API gateway: checks the token, validates input, applies the quota, queues creation, manages links, reports tasks | 128 MiB |
| `creator` | Python 3.12 | Create URL service: pulls tasks in batches, inserts links with collision retry, publishes results | 96 MiB |
| `notifier` | Python 3.12, FastAPI | Notification service: pushes results to the creator over Server-Sent Events, and by e-mail when SMTP is configured | 96 MiB |
| `migrate` | Python 3.12 | creates database users, validators, indexes, streams and consumers, then stays up as a readiness marker | 96 MiB |
| `redirect` | TypeScript, Node 24, Fastify 5 | redirect hot path: read-through cache, `302` / `410` / `404` | 128 MiB |
| `mongo` | MongoDB 7.0 | link and task storage (WiredTiger cache capped at 256 MiB) | 448 MiB |
| `queue` | NATS 2.12 JetStream | the distributed queue; its file store is the log disk | 64 MiB |
| `cache` | Valkey 8.1 | 32 MiB LRU cache, no persistence | 48 MiB |

The four Python services are one codebase and one image. Each runs its own entry point, and the code is layered hexagonally: `domain` → `application` → `adapters` → `entrypoints`.

### Creating a link

1. The browser sends `POST /api/links {"long_url": …}`. oauth2-proxy adds the user's Keycloak access token.
2. The gateway validates the token itself (JWKS signature, `iss`, `aud` = `nanolink`, `exp`, token type) and checks the URL. It never fetches the URL; see [Security](#security). Then it counts the request against the owner's quota for the current UTC day and publishes a task to `links.create.<user id>` with the task id as the JetStream message id, so a retried publish is stored once. JetStream's acknowledgement is **ack 1**; the gateway then answers `202 Accepted` with the task id (**ack 2**).
3. The creator pulls up to 100 tasks at a time. It drops duplicates and reuses the user's existing active link for the same URL. It inserts the rest in one unordered `insert_many`, with timestamps taken from the MongoDB server clock. Unique indexes decide collisions, and a taken short code is retried with a new one. It writes the outcome to the task ledger, which is **ack 3**, and publishes the result. Redelivered tasks are recognised by their task id, so processing is idempotent.
4. The notifier forwards the result to the creator's open `EventSource`, and the new link appears in the UI. `GET /api/tasks/{id}` gives the same answer to clients that poll.

### Serving a click

`GET /{code}` → redirect service → Valkey `link:<code>`:
- On a hit it answers straight away: `302` with the target, `410` for a deleted link, or `404` for an unknown code.
- On a miss it reads MongoDB and caches the answer. Active links are cached for 5 minutes, deleted ones for 1 hour, unknown codes for 30 seconds, which stops floods of unknown codes from reaching the database.
- If Valkey is slow or down (50 ms deadline), it reads MongoDB directly.

Browsers get small HTML error pages; other clients get JSON.

The gateway deletes the cache entry whenever a link changes or is deleted. A redirect that read the old value just before the change can put it back, so a stale target can live at most 5 minutes.

### From the 2024 sketch to what runs

The original design, kept for history: [current design (2024)](docs/iter1.jpg) · [final design sketch (2024)](docs/approximate_final.jpg).

| Sketch | Built as |
|---|---|
| Auth service (black box, 403) | Keycloak realm `luppol` + oauth2-proxy in front; the gateway verifies the access token (401 / 403) |
| API gateway (queue + ack) | `gateway`, JetStream publish acknowledgement → `202` |
| Distributed queue, tasks grouped by user id | NATS JetStream stream `LINK_TASKS`, subjects `links.create.<user id>` |
| Log disk (task duplication) | JetStream file store on a volume; tasks are kept for 7 days |
| Create URL service (batch) | `creator`, pull consumer, batches of 100 |
| Notification service (e-mail) | `notifier`: live SSE to the UI, e-mail through an SMTP adapter |
| Distributed cache (read-through, DB fallback) | Valkey, read-through decorator in the redirect service, 50 ms deadline, MongoDB fallback |
| Redirect service | `redirect` (Fastify) |

**Re-scoped to fit 1.25 GB on a shared 8 GB server:**
- NATS JetStream (≈10 MiB) replaces three Kafka brokers, and one Valkey node replaces a Redis cluster.
- Every stateful service is a single node. JetStream replication is configuration (`num_replicas` on a NATS cluster); a Valkey cluster would also need the cluster-aware clients.
- Tracing (Jaeger) is left out in favour of structured logs.

## Run it locally

Requirements: Docker with Compose ≥ 2.24, `openssl`.

```bash
dev/up.sh        # builds the five images, generates throwaway secrets, starts the stack
open http://127.0.0.1:8088
dev/down.sh      # stops it; add --volumes to drop the data
```

Locally, a small development proxy (`dev/identity/proxy.py`) plays the part of oauth2-proxy and Keycloak. It signs short-lived tokens with its own key and lets you sign in as `alice`, `bob` (users), `admin` or `guest`. The services run exactly the production `deploy/compose.yaml`; only the token issuer, the public URL and the published port differ (`dev/compose.yaml`).

```bash
docker run --rm -i --network nanolink_back nanolink/backend:dev python - < dev/e2e.py
```
This end-to-end check signs in, creates a link through the queue and waits for the pushed result, follows the redirect, re-points and deletes the link, and checks owner isolation, the admin view, the guest sandbox and the input rules.

## API

All `/api` routes need the access token (`X-Forwarded-Access-Token`, set by oauth2-proxy); short-code redirects do not. Errors are `{"error": code, "message": text}`.

| Route | Answer |
|---|---|
| `GET /api/me` | who you are, your roles, today's quota |
| `POST /api/links {long_url}` | `202 {task_id, status: "queued"}` + `Location: /api/tasks/{id}`; `422 invalid_long_url`, `429 quota_exceeded` |
| `GET /api/tasks/{task_id}` | `{task_id, status: queued\|created\|failed, link, failure}` |
| `GET /api/links?cursor=&limit=` | your active links, newest first, `{links, next_cursor}` |
| `GET` / `PATCH {long_url}` / `DELETE /api/links/{id}` | one of your links; `409 duplicate_long_url` when you already have that target |
| `GET /api/admin/links`, `DELETE /api/admin/links/{id}` | moderation, role `ADMIN` |
| `GET /api/notifications` | Server-Sent Events, event `link-result` |
| `GET /{code}` | `302` to the target, `410` deleted, `404` unknown |

The OpenAPI document is served at `/api/openapi.json`.

## Security

- **Tokens:** oauth2-proxy handles the login. The gateway and the notifier still verify every access token themselves: RS256 only, JWKS signature, `iss`, `aud` containing `nanolink`, `exp`, and `typ` = `Bearer`, so an ID token is refused. Roles come from `realm_access.roles`. Tests cover forged, expired, foreign-audience, algorithm-confusion (HS256 signed with the public key) and unsigned tokens.
- **Object-level checks:** every link and task query is scoped to the caller. The guest role works in a shared sandbox; the `demo-reset` command, which the demo server is to run nightly, wipes and reseeds it and restores its quota. Moderation needs `ADMIN`.
- **No server-side requests to user URLs:** NanoLink never fetches a submitted address, so there is no SSRF surface. It still refuses destinations that point into private space: non-http(s) schemes, embedded credentials, loopback, private, link-local and CGNAT addresses (including `169.254.169.254` and IPv4-mapped IPv6), numeric host forms such as `2130706433` or `0x7f.1`, single-label hosts, and internal top-level domains.
- **Least privilege in the data layer:** the MongoDB users are `gateway` and `creator` (readWrite) and `redirect` (read only). A JSON-schema validator guards the `links` collection.
- **Containers:** `cap_drop: [ALL]`, `no-new-privileges`, read-only root filesystems with a small `/tmp`, non-root users, memory and PID limits. The data and service networks are `internal` and have no route out. Of the application services only the gateway and the notifier also join a network with egress, for JWKS and SMTP; `web` joins the network the server's login gateway provides.
- **Dependencies:** Python locked with hashes (`pip-audit`: 0), npm lockfiles (`npm audit`: 0), base images pinned by digest.
- **A known limit:** the deploy contract delivers every secret through one `.env`, so each container holds all of them. The per-service database users protect against bugs, not against a compromised container; per-service secret files would close that gap.

## Tests and quality gates

| Part | Checks | Tests |
|---|---|---|
| `services/backend` | `ruff` (lint + format), `mypy --strict`, house-rule check (no comments or docstrings, functions ≤ 30 lines), `pip-audit` | 47 contract tests (each unit a `CASES` table) + 12 integration tests against real MongoDB, NATS and Valkey |
| `services/redirect` | Biome, `tsc` strict, comment check, `npm audit` | 17 contract tests (Fastify `inject` with in-memory ports) |
| `services/web` | Biome, `tsc` strict, comment check, `npm audit` | 16 contract tests of the UI model; nginx `-t` at image build |
| whole stack | `deploy/smoke.sh`: 12 HTTP checks against the production compose file; `dev/e2e.py`: the signed-in flows | CI jobs `stack` and `e2e` |

CI (`.github/workflows/ci.yml`) runs all of this on every push to `dev`, builds the five images, and brings the production compose file up with `--wait`. `main` is the deploy branch: a green `dev` commit pushed to it is deployed to the demo server by `.github/workflows/deploy.yml`.

## Benchmark

Two scripts, both run in containers on the stack's network, so no host port forwarding sits in the path. The target is a seeded link (`/Albert`), which takes the production route minus Caddy and oauth2-proxy: nginx → redirect → Valkey. Every answer is checked to be a `302`.

**Latency on one keep-alive connection:** `docker run --rm -i --network nanolink_back nanolink/backend:dev python - < bench/latency.py`. It sends 200 warm-up and 2,000 measured sequential requests.

| Path | Req/s | mean | p50 | p90 | p99 | max |
|---|---|---|---|---|---|---|
| through nginx (3 runs) | 622–643 | 1.55–1.60 ms | 1.46–1.50 ms | 1.90–2.03 ms | 2.54–3.08 ms | 6.6–8.4 ms |
| redirect service directly | 744 | 1.34 ms | 1.29 ms | 1.59 ms | 2.17 ms | 12.4 ms |

**Throughput under concurrency:** `bench/redirect.sh` runs [autocannon](https://github.com/mcollina/autocannon) for 30 s at each level after a 5 s warm-up.

| Connections | Requests | Req/s | Socket errors |
|---|---|---|---|
| 1 | 22,649 | 755 | 2 |
| 10 | 103,764 | 3,459 | 1 |
| 50 | 65,272 | 2,176 | 0 |
| 100 | 80,391 | 2,680 | 0 |

**Where it ran:** a 2019 MacBook Pro (Intel i9-9980HK, 8 cores) under Docker Desktop, 2026-09-24 03:45–03:52 UTC. The laptop was shared with other workloads: the load average moved between 6 and 36 during the runs, and throughput varied by up to 3.5× between runs. At 1 and 10 connections autocannon's latency histogram disagreed with its own throughput (Little's law), so latency comes from the sequential script. Treat these as a floor on a busy developer machine; the same scripts will run on the demo server.

## Repository

```
services/backend    Python: domain, application, adapters (MongoDB, NATS, Valkey, OIDC, SMTP), entrypoints
services/redirect   TypeScript: redirect service
services/web        nginx config, UI source, demo-reset command
services/queue      NATS JetStream configuration
services/cache      Valkey start script
deploy/             production compose file, image list, secret names, smoke checks
dev/                local override, development sign-in proxy, end-to-end check
bench/              redirect benchmark
.github/workflows   ci.yml (dev), deploy.yml (main → demo server)
```

## License

GNU Affero General Public License v3.0. Contact: [albert.y.luppol@gmail.com](mailto:albert.y.luppol@gmail.com).
