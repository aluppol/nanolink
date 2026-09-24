import type { FastifyInstance, FastifyReply } from "fastify";
import type { ReadinessProbe } from "../domain/readinessProbe.js";

const ALIVE = { status: "ok" } as const;
const READY = { status: "ready" } as const;
const NOT_READY = { status: "unavailable" } as const;

export function registerHealthRoutes(server: FastifyInstance, readiness: ReadinessProbe): void {
  server.get("/healthz", (_request, reply) =>
    reply.header("cache-control", "no-store").send(ALIVE),
  );
  server.get("/readyz", (_request, reply) => answerReadiness(readiness, reply));
}

async function answerReadiness(
  readiness: ReadinessProbe,
  reply: FastifyReply,
): Promise<FastifyReply> {
  const isReady = await readiness.isReady();
  return reply
    .code(isReady ? 200 : 503)
    .header("cache-control", "no-store")
    .send(isReady ? READY : NOT_READY);
}
