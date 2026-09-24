import assert from "node:assert/strict";
import { test } from "node:test";
import {
  cacheKeyOf,
  cacheLifetimeSeconds,
  decodeCacheEntry,
  encodeCacheEntry,
} from "../src/adapters/cacheEntryCodec.js";
import {
  activeLink,
  DELETED_LINK,
  type LinkResolution,
  MISSING_LINK,
} from "../src/domain/linkResolution.js";
import { type Case, mismatchesOf } from "./support/cases.js";

interface Encoded {
  readonly entry: string;
  readonly lifetimeSeconds: number;
}

const ENCODE_CASES: readonly Case<LinkResolution, Encoded>[] = [
  {
    id: "active keeps the destination under long_url for five minutes",
    input: activeLink("https://example.org/a?b=1"),
    expected: {
      entry: '{"state":"active","long_url":"https://example.org/a?b=1"}',
      lifetimeSeconds: 300,
    },
  },
  {
    id: "deleted lives an hour",
    input: DELETED_LINK,
    expected: { entry: '{"state":"deleted"}', lifetimeSeconds: 3600 },
  },
  {
    id: "missing lives thirty seconds",
    input: MISSING_LINK,
    expected: { entry: '{"state":"missing"}', lifetimeSeconds: 30 },
  },
];

const DECODE_CASES: readonly Case<string, LinkResolution | undefined>[] = [
  {
    id: "active entry",
    input: '{"state":"active","long_url":"https://example.org/"}',
    expected: activeLink("https://example.org/"),
  },
  { id: "deleted entry", input: '{"state":"deleted"}', expected: DELETED_LINK },
  { id: "missing entry", input: '{"state":"missing"}', expected: MISSING_LINK },
  { id: "active without a destination", input: '{"state":"active"}', expected: undefined },
  {
    id: "destination of the wrong type",
    input: '{"state":"active","long_url":7}',
    expected: undefined,
  },
  { id: "unknown state", input: '{"state":"archived"}', expected: undefined },
  { id: "not JSON", input: "https://example.org/", expected: undefined },
  { id: "JSON array", input: '["active"]', expected: undefined },
  { id: "JSON null", input: "null", expected: undefined },
];

test("encodeCacheEntry writes the §10 cache JSON with its lifetime", async () => {
  const encode = (resolution: LinkResolution): Encoded => ({
    entry: encodeCacheEntry(resolution),
    lifetimeSeconds: cacheLifetimeSeconds(resolution),
  });
  assert.deepEqual(await mismatchesOf(ENCODE_CASES, encode), []);
});

test("decodeCacheEntry reads only well-formed entries", async () => {
  assert.deepEqual(await mismatchesOf(DECODE_CASES, decodeCacheEntry), []);
});

test("cache keys are link:<code>", () => {
  assert.equal(cacheKeyOf("aB3xY9"), "link:aB3xY9");
});
