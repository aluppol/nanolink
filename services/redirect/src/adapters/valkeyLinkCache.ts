import type { LinkResolution } from "../domain/linkResolution.js";
import {
  cacheKeyOf,
  cacheLifetimeSeconds,
  decodeCacheEntry,
  encodeCacheEntry,
} from "./cacheEntryCodec.js";
import { DEADLINE_PASSED, settleWithin } from "./deadline.js";
import {
  CACHE_MISS,
  CACHE_UNAVAILABLE,
  type CacheLookup,
  cacheHit,
  type LinkCache,
} from "./linkCache.js";

export interface KeyValueStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string, secondsToken: "EX", seconds: number): Promise<unknown>;
}

export class ValkeyLinkCache implements LinkCache {
  readonly #store: KeyValueStore;
  readonly #deadlineMilliseconds: number;

  constructor(store: KeyValueStore, deadlineMilliseconds: number) {
    this.#store = store;
    this.#deadlineMilliseconds = deadlineMilliseconds;
  }

  async lookup(shortCode: string): Promise<CacheLookup> {
    try {
      const entry = await settleWithin(
        this.#store.get(cacheKeyOf(shortCode)),
        this.#deadlineMilliseconds,
      );
      return entry === DEADLINE_PASSED ? CACHE_UNAVAILABLE : lookupOf(entry);
    } catch {
      return CACHE_UNAVAILABLE;
    }
  }

  async store(shortCode: string, resolution: LinkResolution): Promise<void> {
    const write = this.#store.set(
      cacheKeyOf(shortCode),
      encodeCacheEntry(resolution),
      "EX",
      cacheLifetimeSeconds(resolution),
    );
    await settleWithin(write, this.#deadlineMilliseconds).catch(() => undefined);
  }
}

function lookupOf(entry: string | null): CacheLookup {
  const resolution = entry === null ? undefined : decodeCacheEntry(entry);
  return resolution === undefined ? CACHE_MISS : cacheHit(resolution);
}
