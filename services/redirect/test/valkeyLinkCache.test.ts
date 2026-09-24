import assert from "node:assert/strict";
import { test } from "node:test";
import {
  CACHE_MISS,
  CACHE_UNAVAILABLE,
  type CacheLookup,
  cacheHit,
} from "../src/adapters/linkCache.js";
import { type KeyValueStore, ValkeyLinkCache } from "../src/adapters/valkeyLinkCache.js";
import {
  activeLink,
  DELETED_LINK,
  type LinkResolution,
  MISSING_LINK,
} from "../src/domain/linkResolution.js";
import { type Case, mismatchesOf } from "./support/cases.js";
import {
  FailingKeyValueStore,
  HangingKeyValueStore,
  InMemoryKeyValueStore,
  type KeyValueWrite,
} from "./support/fakes.js";

const DEADLINE_MILLISECONDS = 20;

const STORED = new InMemoryKeyValueStore({
  "link:aB3xY9": '{"state":"active","long_url":"https://example.org/"}',
  "link:dE1eT3": '{"state":"deleted"}',
  "link:mI55nG": '{"state":"missing"}',
  "link:bR0k3n": "{not json",
});

interface LookupInput {
  readonly store: KeyValueStore;
  readonly shortCode: string;
}

const LOOKUP_CASES: readonly Case<LookupInput, CacheLookup>[] = [
  {
    id: "active entry is a hit",
    input: { store: STORED, shortCode: "aB3xY9" },
    expected: cacheHit(activeLink("https://example.org/")),
  },
  {
    id: "deleted entry is a hit",
    input: { store: STORED, shortCode: "dE1eT3" },
    expected: cacheHit(DELETED_LINK),
  },
  {
    id: "missing entry is a hit",
    input: { store: STORED, shortCode: "mI55nG" },
    expected: cacheHit(MISSING_LINK),
  },
  {
    id: "absent key is a miss",
    input: { store: STORED, shortCode: "n0Th3r" },
    expected: CACHE_MISS,
  },
  {
    id: "corrupt entry is a miss",
    input: { store: STORED, shortCode: "bR0k3n" },
    expected: CACHE_MISS,
  },
  {
    id: "failing store is unavailable",
    input: { store: new FailingKeyValueStore(), shortCode: "aB3xY9" },
    expected: CACHE_UNAVAILABLE,
  },
  {
    id: "store slower than the deadline is unavailable",
    input: { store: new HangingKeyValueStore(), shortCode: "aB3xY9" },
    expected: CACHE_UNAVAILABLE,
  },
];

interface CacheWrite {
  readonly shortCode: string;
  readonly resolution: LinkResolution;
}

const STORE_CASES: readonly Case<CacheWrite, KeyValueWrite[]>[] = [
  {
    id: "active is written for 300 s",
    input: { shortCode: "aB3xY9", resolution: activeLink("https://example.org/") },
    expected: [
      {
        key: "link:aB3xY9",
        value: '{"state":"active","long_url":"https://example.org/"}',
        seconds: 300,
      },
    ],
  },
  {
    id: "deleted is written for 3600 s",
    input: { shortCode: "dE1eT3", resolution: DELETED_LINK },
    expected: [{ key: "link:dE1eT3", value: '{"state":"deleted"}', seconds: 3600 }],
  },
  {
    id: "missing is written for 30 s",
    input: { shortCode: "mI55nG", resolution: MISSING_LINK },
    expected: [{ key: "link:mI55nG", value: '{"state":"missing"}', seconds: 30 }],
  },
];

async function writesOf(write: CacheWrite): Promise<KeyValueWrite[]> {
  const store = new InMemoryKeyValueStore({});
  await new ValkeyLinkCache(store, DEADLINE_MILLISECONDS).store(write.shortCode, write.resolution);
  return store.writes;
}

test("ValkeyLinkCache.lookup turns every store answer into hit, miss or unavailable", async () => {
  const lookUp = ({ store, shortCode }: LookupInput): Promise<CacheLookup> =>
    new ValkeyLinkCache(store, DEADLINE_MILLISECONDS).lookup(shortCode);
  assert.deepEqual(await mismatchesOf(LOOKUP_CASES, lookUp), []);
});

test("ValkeyLinkCache.store writes the §10 key, JSON and lifetime", async () => {
  assert.deepEqual(await mismatchesOf(STORE_CASES, writesOf), []);
});

test("ValkeyLinkCache.store never throws when the store fails or hangs", async () => {
  const stores = [new FailingKeyValueStore(), new HangingKeyValueStore()];
  for (const store of stores) {
    await new ValkeyLinkCache(store, DEADLINE_MILLISECONDS).store("aB3xY9", MISSING_LINK);
  }
});
