import assert from "node:assert/strict";
import { test } from "node:test";
import {
  cacheKeyOf,
  cacheLifetimeSeconds,
  decodeCacheEntry,
  encodeCacheEntry,
} from "../src/adapters/cacheEntryCodec.js";
import {
  DELETED_LINK,
  type LinkResolution,
  MISSING_LINK,
  trustedLink,
  untrustedLink,
} from "../src/domain/linkResolution.js";
import { type Case, mismatchesOf } from "./support/cases.js";

interface Encoded {
  readonly entry: string;
  readonly lifetimeSeconds: number;
}

const ENCODE_CASES: readonly Case<LinkResolution, Encoded>[] = [
  {
    id: "trusted keeps the destination under long_url for five minutes",
    input: trustedLink("https://example.org/a?b=1"),
    expected: {
      entry: '{"version":3,"state":"trusted","long_url":"https://example.org/a?b=1"}',
      lifetimeSeconds: 300,
    },
  },
  {
    id: "untrusted keeps the destination under long_url for five minutes",
    input: untrustedLink("https://example.org/a?b=1"),
    expected: {
      entry: '{"version":3,"state":"untrusted","long_url":"https://example.org/a?b=1"}',
      lifetimeSeconds: 300,
    },
  },
  {
    id: "deleted lives an hour",
    input: DELETED_LINK,
    expected: { entry: '{"version":3,"state":"deleted"}', lifetimeSeconds: 3600 },
  },
  {
    id: "missing lives thirty seconds",
    input: MISSING_LINK,
    expected: { entry: '{"version":3,"state":"missing"}', lifetimeSeconds: 30 },
  },
];

const DECODE_CASES: readonly Case<string, LinkResolution | undefined>[] = [
  {
    id: "trusted entry",
    input: '{"version":3,"state":"trusted","long_url":"https://example.org/"}',
    expected: trustedLink("https://example.org/"),
  },
  {
    id: "untrusted entry",
    input: '{"version":3,"state":"untrusted","long_url":"https://example.org/"}',
    expected: untrustedLink("https://example.org/"),
  },
  { id: "deleted entry", input: '{"version":3,"state":"deleted"}', expected: DELETED_LINK },
  { id: "missing entry", input: '{"version":3,"state":"missing"}', expected: MISSING_LINK },
  {
    id: "trusted without a destination",
    input: '{"version":3,"state":"trusted"}',
    expected: undefined,
  },
  {
    id: "untrusted without a destination",
    input: '{"version":3,"state":"untrusted"}',
    expected: undefined,
  },
  {
    id: "destination of the wrong type",
    input: '{"version":3,"state":"trusted","long_url":7}',
    expected: undefined,
  },
  { id: "unknown state", input: '{"version":3,"state":"archived"}', expected: undefined },
  {
    id: "the previous release's redirecting state is unknown in this format",
    input: '{"version":3,"state":"active","long_url":"https://example.org/"}',
    expected: undefined,
  },
  {
    id: "the previous release's sandbox state is unknown in this format",
    input: '{"version":3,"state":"sandboxed","long_url":"https://example.org/"}',
    expected: undefined,
  },
  {
    id: "an entry the previous release wrote for a member's link is a miss, so it cannot redirect",
    input: '{"version":2,"state":"active","long_url":"https://example.org/"}',
    expected: undefined,
  },
  {
    id: "entry from before the format had a version is a miss",
    input: '{"state":"trusted","long_url":"https://example.org/"}',
    expected: undefined,
  },
  {
    id: "entry of a later format version is a miss",
    input: '{"version":4,"state":"trusted","long_url":"https://example.org/"}',
    expected: undefined,
  },
  { id: "not JSON", input: "https://example.org/", expected: undefined },
  { id: "JSON array", input: '["trusted"]', expected: undefined },
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
