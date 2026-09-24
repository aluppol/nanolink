import assert from "node:assert/strict";
import { test } from "node:test";
import {
  CACHE_MISS,
  CACHE_UNAVAILABLE,
  type CacheLookup,
  cacheHit,
} from "../src/adapters/linkCache.js";
import { ReadThroughLinkSource } from "../src/adapters/readThroughLinkSource.js";
import {
  activeLink,
  DELETED_LINK,
  type LinkResolution,
  MISSING_LINK,
} from "../src/domain/linkResolution.js";
import { type Case, mismatchesOf } from "./support/cases.js";
import {
  InMemoryLinkCache,
  InMemoryLinkSource,
  type StoredEntry,
  UnreachableLinkSource,
} from "./support/fakes.js";

const CODE = "aB3xY9";
const DESTINATION = activeLink("https://example.org/");

interface Situation {
  readonly cached: CacheLookup;
  readonly inDatabase: LinkResolution;
}

interface Outcome {
  readonly resolution: LinkResolution;
  readonly askedDatabaseFor: readonly string[];
  readonly cachedAfterwards: readonly StoredEntry[];
}

const CASES: readonly Case<Situation, Outcome>[] = [
  {
    id: "cached active link skips the database",
    input: { cached: cacheHit(DESTINATION), inDatabase: DELETED_LINK },
    expected: { resolution: DESTINATION, askedDatabaseFor: [], cachedAfterwards: [] },
  },
  {
    id: "cached deleted link skips the database",
    input: { cached: cacheHit(DELETED_LINK), inDatabase: DESTINATION },
    expected: { resolution: DELETED_LINK, askedDatabaseFor: [], cachedAfterwards: [] },
  },
  {
    id: "cached missing link skips the database",
    input: { cached: cacheHit(MISSING_LINK), inDatabase: DESTINATION },
    expected: { resolution: MISSING_LINK, askedDatabaseFor: [], cachedAfterwards: [] },
  },
  {
    id: "miss reads the database and caches the active link",
    input: { cached: CACHE_MISS, inDatabase: DESTINATION },
    expected: {
      resolution: DESTINATION,
      askedDatabaseFor: [CODE],
      cachedAfterwards: [{ shortCode: CODE, resolution: DESTINATION }],
    },
  },
  {
    id: "miss reads the database and caches the deletion",
    input: { cached: CACHE_MISS, inDatabase: DELETED_LINK },
    expected: {
      resolution: DELETED_LINK,
      askedDatabaseFor: [CODE],
      cachedAfterwards: [{ shortCode: CODE, resolution: DELETED_LINK }],
    },
  },
  {
    id: "miss reads the database and caches the absence",
    input: { cached: CACHE_MISS, inDatabase: MISSING_LINK },
    expected: {
      resolution: MISSING_LINK,
      askedDatabaseFor: [CODE],
      cachedAfterwards: [{ shortCode: CODE, resolution: MISSING_LINK }],
    },
  },
  {
    id: "unavailable cache falls back to the database and writes nothing",
    input: { cached: CACHE_UNAVAILABLE, inDatabase: DESTINATION },
    expected: { resolution: DESTINATION, askedDatabaseFor: [CODE], cachedAfterwards: [] },
  },
];

async function resolveThrough(situation: Situation): Promise<Outcome> {
  const cache = new InMemoryLinkCache({ [CODE]: situation.cached });
  const database = new InMemoryLinkSource({ [CODE]: situation.inDatabase });
  const resolution = await new ReadThroughLinkSource(cache, database).resolve(CODE);
  return { resolution, askedDatabaseFor: database.requestedCodes, cachedAfterwards: cache.stored };
}

test("ReadThroughLinkSource answers from the cache, else from the database", async () => {
  assert.deepEqual(await mismatchesOf(CASES, resolveThrough), []);
});

test("ReadThroughLinkSource lets a database failure through and caches nothing", async () => {
  const cache = new InMemoryLinkCache({});
  const source = new ReadThroughLinkSource(cache, new UnreachableLinkSource());
  await assert.rejects(source.resolve(CODE), /database unreachable/);
  assert.deepEqual(cache.stored, []);
});
