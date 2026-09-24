import type { FastifyBaseLogger, FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import type { LinkResolution } from "../domain/linkResolution.js";
import type { LinkResolver } from "../domain/linkResolver.js";
import { replyWithError, replyWithResolution } from "./replies.js";
import { representationFor } from "./representations.js";

interface LinkRequest {
  readonly Params: { readonly code: string };
}

export function registerRedirectRoutes(server: FastifyInstance, resolver: LinkResolver): void {
  server.get<LinkRequest>("/:code", (request, reply) =>
    answerLinkRequest(resolver, request, reply),
  );
  server.setNotFoundHandler((request, reply) => replyNotFound(request, reply));
}

export function replyNotFound(request: FastifyRequest, reply: FastifyReply): FastifyReply {
  const representation = representationFor(request.headers.accept);
  return replyWithError(reply, 404, representation.contentType, representation.notFound);
}

async function answerLinkRequest(
  resolver: LinkResolver,
  request: FastifyRequest<LinkRequest>,
  reply: FastifyReply,
): Promise<FastifyReply> {
  const representation = representationFor(request.headers.accept);
  const resolution = await resolveReportingFailure(resolver, request.params.code, request.log);
  if (resolution === undefined) {
    return replyWithError(reply, 503, representation.contentType, representation.unavailable);
  }
  return replyWithResolution(reply, resolution, representation);
}

async function resolveReportingFailure(
  resolver: LinkResolver,
  code: string,
  log: FastifyBaseLogger,
): Promise<LinkResolution | undefined> {
  try {
    return await resolver.resolve(code);
  } catch (error) {
    log.error({ err: error }, "link lookup failed");
    return undefined;
  }
}
