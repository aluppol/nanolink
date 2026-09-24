import assert from "node:assert/strict";
import { after, test } from "node:test";
import type { FastifyInstance, InjectOptions } from "fastify";
import { activeLink, DELETED_LINK } from "../src/domain/linkResolution.js";
import { LinkResolver } from "../src/domain/linkResolver.js";
import type { LinkSource } from "../src/domain/linkSource.js";
import { PAGE_SECURITY_POLICY } from "../src/http/pages.js";
import { buildServer } from "../src/http/server.js";
import { type Case, mismatchesOf } from "./support/cases.js";
import { InMemoryLinkSource, READY_PROBE, UnreachableLinkSource } from "./support/fakes.js";

const BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8";
const JSON_ACCEPT = "application/json";

interface Observed {
  readonly status: number;
  readonly location?: string;
  readonly cacheControl?: string;
  readonly securityPolicy?: string;
  readonly body: string;
}

const LINKS = new InMemoryLinkSource({
  aB3xY9: activeLink("https://example.org/path?q=1"),
  uN1c0d: activeLink("https://exämple.org/ü"),
  dE1eT3: DELETED_LINK,
});

const HEALTHY_SERVER = serverWith(LINKS);
const BROKEN_DATABASE_SERVER = serverWith(new UnreachableLinkSource());

after(async () => {
  await Promise.all([HEALTHY_SERVER.close(), BROKEN_DATABASE_SERVER.close()]);
});

const NO_STORE = "no-store";
const FOUND = { status: 302, cacheControl: NO_STORE, body: "" } as const;

function errorAnswer(status: number, body: string): Observed {
  return { status, cacheControl: NO_STORE, securityPolicy: PAGE_SECURITY_POLICY, body };
}

const CASES: readonly Case<InjectOptions, Observed>[] = [
  {
    id: "active code redirects with no-store",
    input: { method: "GET", url: "/aB3xY9", headers: { accept: BROWSER_ACCEPT } },
    expected: { ...FOUND, location: "https://example.org/path?q=1" },
  },
  {
    id: "HEAD behaves like GET",
    input: { method: "HEAD", url: "/aB3xY9" },
    expected: { ...FOUND, location: "https://example.org/path?q=1" },
  },
  {
    id: "query string on the short link is ignored",
    input: { method: "GET", url: "/aB3xY9?utm_source=mail" },
    expected: { ...FOUND, location: "https://example.org/path?q=1" },
  },
  {
    id: "non-ASCII destination is sent as an ASCII header",
    input: { method: "GET", url: "/uN1c0d" },
    expected: { ...FOUND, location: "https://xn--exmple-cua.org/%C3%BC" },
  },
  {
    id: "deleted code is 410 JSON for API clients",
    input: { method: "GET", url: "/dE1eT3", headers: { accept: JSON_ACCEPT } },
    expected: errorAnswer(410, 'json:{"error":"gone"}'),
  },
  {
    id: "deleted code is a 410 page for browsers",
    input: { method: "GET", url: "/dE1eT3", headers: { accept: BROWSER_ACCEPT } },
    expected: errorAnswer(410, "html:This link was deleted"),
  },
  {
    id: "unknown code is 404 JSON without an Accept header",
    input: { method: "GET", url: "/zZ9zZ9" },
    expected: errorAnswer(404, 'json:{"error":"not_found"}'),
  },
  {
    id: "unknown code is a 404 page for browsers",
    input: { method: "GET", url: "/zZ9zZ9", headers: { accept: BROWSER_ACCEPT } },
    expected: errorAnswer(404, "html:This link doesn't exist"),
  },
  {
    id: "five-character path is 404",
    input: { method: "GET", url: "/aB3xY", headers: { accept: JSON_ACCEPT } },
    expected: errorAnswer(404, 'json:{"error":"not_found"}'),
  },
  {
    id: "nested path is 404",
    input: { method: "GET", url: "/aB3xY9/more", headers: { accept: JSON_ACCEPT } },
    expected: errorAnswer(404, 'json:{"error":"not_found"}'),
  },
  {
    id: "root is 404",
    input: { method: "GET", url: "/", headers: { accept: BROWSER_ACCEPT } },
    expected: errorAnswer(404, "html:This link doesn't exist"),
  },
  {
    id: "POST to a code is 404",
    input: { method: "POST", url: "/aB3xY9", headers: { accept: JSON_ACCEPT } },
    expected: errorAnswer(404, 'json:{"error":"not_found"}'),
  },
  {
    id: "malformed percent-encoding is 404",
    input: { method: "GET", url: "/%zz%zz", headers: { accept: JSON_ACCEPT } },
    expected: errorAnswer(404, 'json:{"error":"not_found"}'),
  },
];

const BROKEN_DATABASE_CASES: readonly Case<InjectOptions, Observed>[] = [
  {
    id: "database failure is 503 JSON",
    input: { method: "GET", url: "/aB3xY9", headers: { accept: JSON_ACCEPT } },
    expected: errorAnswer(503, 'json:{"error":"unavailable"}'),
  },
  {
    id: "database failure is a 503 page for browsers",
    input: { method: "GET", url: "/aB3xY9", headers: { accept: BROWSER_ACCEPT } },
    expected: errorAnswer(503, "html:NanoLink is temporarily unavailable"),
  },
  {
    id: "malformed code never reaches the database",
    input: { method: "GET", url: "/not-a-code", headers: { accept: JSON_ACCEPT } },
    expected: errorAnswer(404, 'json:{"error":"not_found"}'),
  },
];

test("GET /:code answers 302, 404 or 410 in the representation the client accepts", async () => {
  assert.deepEqual(await mismatchesOf(CASES, (request) => observe(HEALTHY_SERVER, request)), []);
});

test("GET /:code answers 503 when the database cannot be read", async () => {
  const observeBroken = (request: InjectOptions): Promise<Observed> =>
    observe(BROKEN_DATABASE_SERVER, request);
  assert.deepEqual(await mismatchesOf(BROKEN_DATABASE_CASES, observeBroken), []);
});

function serverWith(source: LinkSource): FastifyInstance {
  return buildServer({
    resolver: new LinkResolver(source),
    readiness: READY_PROBE,
    logLevel: "silent",
  });
}

async function observe(server: FastifyInstance, request: InjectOptions): Promise<Observed> {
  const response = await server.inject(request);
  return withoutAbsentFields({
    status: response.statusCode,
    location: headerText(response.headers.location),
    cacheControl: headerText(response.headers["cache-control"]),
    securityPolicy: headerText(response.headers["content-security-policy"]),
    body: summarize(headerText(response.headers["content-type"]), response.body),
  });
}

function headerText(value: string | string[] | number | undefined): string | undefined {
  return value === undefined ? undefined : String(value);
}

function summarize(contentType: string | undefined, body: string): string {
  if (contentType?.startsWith("text/html") === true) {
    return `html:${/<h1>(.*?)<\/h1>/.exec(body)?.[1] ?? "no heading"}`;
  }
  if (contentType?.startsWith("application/json") === true) {
    return `json:${JSON.stringify(JSON.parse(body))}`;
  }
  return body;
}

function withoutAbsentFields(observed: Record<string, unknown>): Observed {
  return Object.fromEntries(
    Object.entries(observed).filter(([, value]) => value !== undefined),
  ) as unknown as Observed;
}
