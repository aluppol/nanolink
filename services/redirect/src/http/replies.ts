import type { FastifyReply } from "fastify";
import type { LinkResolution } from "../domain/linkResolution.js";
import { PAGE_SECURITY_POLICY } from "./pages.js";
import type { Representation } from "./representations.js";

export function replyWithResolution(
  reply: FastifyReply,
  resolution: LinkResolution,
  representation: Representation,
): FastifyReply {
  switch (resolution.state) {
    case "active":
      return replyWithRedirect(reply, resolution.longUrl);
    case "sandboxed":
      return replyWithContent(
        reply,
        200,
        representation.contentType,
        representation.sandboxed(new URL(resolution.longUrl)),
      );
    case "deleted":
      return replyWithContent(reply, 410, representation.contentType, representation.gone);
    case "missing":
      return replyWithContent(reply, 404, representation.contentType, representation.notFound);
  }
}

export function replyWithContent(
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
