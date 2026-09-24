import assert from "node:assert/strict";
import { after, test } from "node:test";
import type { FastifyInstance } from "fastify";
import { LinkResolver } from "../src/domain/linkResolver.js";
import type { ReadinessProbe } from "../src/domain/readinessProbe.js";
import { buildServer } from "../src/http/server.js";
import { type Case, mismatchesOf } from "./support/cases.js";
import { InMemoryLinkSource, READY_PROBE, UNREADY_PROBE } from "./support/fakes.js";

interface Probe {
  readonly server: FastifyInstance;
  readonly url: string;
}

interface Answer {
  readonly status: number;
  readonly body: unknown;
}

const READY_SERVER = serverWith(READY_PROBE);
const UNREADY_SERVER = serverWith(UNREADY_PROBE);

after(async () => {
  await Promise.all([READY_SERVER.close(), UNREADY_SERVER.close()]);
});

const CASES: readonly Case<Probe, Answer>[] = [
  {
    id: "liveness is ok while the database is reachable",
    input: { server: READY_SERVER, url: "/healthz" },
    expected: { status: 200, body: { status: "ok" } },
  },
  {
    id: "liveness stays ok while the database is unreachable",
    input: { server: UNREADY_SERVER, url: "/healthz" },
    expected: { status: 200, body: { status: "ok" } },
  },
  {
    id: "readiness is 200 when the database answers a ping",
    input: { server: READY_SERVER, url: "/readyz" },
    expected: { status: 200, body: { status: "ready" } },
  },
  {
    id: "readiness is 503 when the database does not answer",
    input: { server: UNREADY_SERVER, url: "/readyz" },
    expected: { status: 503, body: { status: "unavailable" } },
  },
];

function serverWith(readiness: ReadinessProbe): FastifyInstance {
  return buildServer({
    resolver: new LinkResolver(new InMemoryLinkSource({})),
    readiness,
    logLevel: "silent",
  });
}

async function answerOf({ server, url }: Probe): Promise<Answer> {
  const response = await server.inject({ method: "GET", url });
  return { status: response.statusCode, body: response.json() };
}

test("health endpoints report liveness and database readiness", async () => {
  assert.deepEqual(await mismatchesOf(CASES, answerOf), []);
});
