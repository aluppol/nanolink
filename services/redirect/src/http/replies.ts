import type { FastifyReply } from "fastify";
import type { LinkResolution } from "../domain/linkResolution.js";
import { PAGE_SECURITY_POLICY } from "./pages.js";
import type { ErrorRepresentation } from "./representations.js";

export function replyWithResolution(
  reply: FastifyReply,
  resolution: LinkResolution,
  representation: ErrorRepresentation,
): FastifyReply {
  switch (resolution.state) {
    case "active":
      return replyWithRedirect(reply, resolution.longUrl);
    case "deleted":
      return replyWithError(reply, 410, representation.contentType, representation.gone);
    case "missing":
      return replyWithError(reply, 404, representation.contentType, representation.notFound);
  }
}

export function replyWithError(
  reply: FastifyReply,
  statusCode: number,
  contentType: string,
  body: string,
): FastifyReply {
  return reply
    .code(statusCode)
    .header("cache-control", "no-store")
    .header("content-security-policy", PAGE_SECURITY_POLICY)
    .type(contentType)
    .send(body);
}

function replyWithRedirect(reply: FastifyReply, longUrl: string): FastifyReply {
  return reply.header("cache-control", "no-store").redirect(new URL(longUrl).href, 302);
}
