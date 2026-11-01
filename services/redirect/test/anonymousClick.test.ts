import assert from "node:assert/strict";
import { after, test } from "node:test";
import type { InjectOptions } from "fastify";
import type { Collection } from "mongodb";
import { type LinkRecord, MongoLinkSource } from "../src/adapters/mongoLinkSource.js";
import { LinkResolver } from "../src/domain/linkResolver.js";
import { buildServer } from "../src/http/server.js";
import { type Case, mismatchesOf } from "./support/cases.js";
import { READY_PROBE } from "./support/fakes.js";

const ADMIN_ID = "0b7d4c1e-0000-4000-8000-00000000ad31";
const MEMBER_ID = "0b7d4c1e-0000-4000-8000-00000000a11c";
const DOCUMENT_ID = "65f0c1f6e8a3b4c2d9e1f0a1";
const STORED_AT = new Date("2025-01-02T03:04:05Z");
const OWNER_DATA = [ADMIN_ID, MEMBER_ID, "sandbox", "task-of-", DOCUMENT_ID, "2025-01-02"];

const STORED: Readonly<Record<string, Readonly<Record<string, unknown>>>> = {
  Trust1: storedLink("Trust1", ADMIN_ID, true, null),
  Membr1: storedLink("Membr1", MEMBER_ID, false, null),
  Sandb1: storedLink("Sandb1", "sandbox", false, null),
  Gone01: storedLink("Gone01", MEMBER_ID, false, STORED_AT),
};

const SERVER = buildServer({
  resolver: new LinkResolver(new MongoLinkSource(storedCollection())),
  readiness: READY_PROBE,
  logLevel: "silent",
});

after(async () => {
  await SERVER.close();
});

interface Observed {
  readonly status: number;
  readonly ownerDataShown: readonly string[];
}

const EXPECTED_STATUS: Readonly<Record<string, number>> = {
  Trust1: 302,
  Membr1: 200,
  Sandb1: 200,
  Gone01: 410,
  Unkn01: 404,
};

const REQUESTS: readonly Omit<InjectOptions, "url">[] = [
  { method: "GET" },
  { method: "GET", headers: { accept: "text/html" } },
  { method: "HEAD" },
];

const CASES: readonly Case<InjectOptions, Observed>[] = Object.entries(EXPECTED_STATUS).flatMap(
  ([code, status]) =>
    REQUESTS.map((request) => ({
      id: `anonymous ${request.method} /${code} ${JSON.stringify(request.headers ?? {})}`,
      input: { ...request, url: `/${code}` },
      expected: { status, ownerDataShown: [] },
    })),
);

function storedLink(
  shortCode: string,
  ownerId: string,
  isTrusted: boolean,
  deletedAt: Date | null,
): Readonly<Record<string, unknown>> {
  return {
    _id: DOCUMENT_ID,
    short_code: shortCode,
    long_url: `https://example.org/${shortCode}`,
    owner_id: ownerId,
    task_id: `task-of-${ownerId}`,
    trusted: isTrusted,
    created_at: STORED_AT,
    updated_at: STORED_AT,
    deleted_at: deletedAt,
  };
}

function storedCollection(): Collection<LinkRecord> {
  const findOne = (filter: { readonly short_code: string }): Promise<unknown> =>
    Promise.resolve(STORED[filter.short_code] ?? null);
  return { findOne } as unknown as Collection<LinkRecord>;
}

async function observe(request: InjectOptions): Promise<Observed> {
  const response = await SERVER.inject(request);
  const everythingSent = `${JSON.stringify(response.headers)}\n${response.body}`;
  return {
    status: response.statusCode,
    ownerDataShown: OWNER_DATA.filter((secret) => everythingSent.includes(secret)),
  };
}

test("an anonymous click gets its answer and nothing about the link's owner", async () => {
  assert.deepEqual(await mismatchesOf(CASES, observe), []);
});
