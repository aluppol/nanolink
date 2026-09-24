import {
  type FastifyError,
  type FastifyInstance,
  type FastifyReply,
  type FastifyRequest,
  fastify,
  LogController,
} from "fastify";
import type { LinkResolver } from "../domain/linkResolver.js";
import type { ReadinessProbe } from "../domain/readinessProbe.js";
import { registerHealthRoutes } from "./healthRoutes.js";
import { registerRedirectRoutes, replyNotFound } from "./redirectRoutes.js";
import { replyWithError } from "./replies.js";
import { representationFor } from "./representations.js";

export interface RedirectServerParts {
  readonly resolver: LinkResolver;
  readonly readiness: ReadinessProbe;
  readonly logLevel: string;
}

export function buildServer(parts: RedirectServerParts): FastifyInstance {
  const server = fastify({
    logger: { level: parts.logLevel },
    logController: new LogController({ disableRequestLogging: true }),
    frameworkErrors: replyToFailure,
    return503OnClosing: true,
  });
  server.setErrorHandler(replyToFailure);
  registerHealthRoutes(server, parts.readiness);
  registerRedirectRoutes(server, parts.resolver);
  return server;
}

function replyToFailure(
  error: FastifyError,
  request: FastifyRequest,
  reply: FastifyReply,
): FastifyReply {
  if (isClientError(error)) {
    return replyNotFound(request, reply);
  }
  request.log.error({ err: error }, "request failed");
  const representation = representationFor(request.headers.accept);
  return replyWithError(reply, 500, representation.contentType, representation.internalError);
}

function isClientError(error: FastifyError): boolean {
  return error.statusCode !== undefined && error.statusCode >= 400 && error.statusCode < 500;
}
