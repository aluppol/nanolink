import { CACHE_MISS, type CacheLookup, type LinkCache } from "../../src/adapters/linkCache.js";
import type { KeyValueStore } from "../../src/adapters/valkeyLinkCache.js";
import { type LinkResolution, MISSING_LINK } from "../../src/domain/linkResolution.js";
import type { LinkSource } from "../../src/domain/linkSource.js";
import type { ReadinessProbe } from "../../src/domain/readinessProbe.js";

export class InMemoryLinkSource implements LinkSource {
  readonly requestedCodes: string[] = [];
  readonly #resolutions: ReadonlyMap<string, LinkResolution>;

  constructor(resolutions: Readonly<Record<string, LinkResolution>>) {
    this.#resolutions = new Map(Object.entries(resolutions));
  }

  resolve(shortCode: string): Promise<LinkResolution> {
    this.requestedCodes.push(shortCode);
    return Promise.resolve(this.#resolutions.get(shortCode) ?? MISSING_LINK);
  }
}

export class UnreachableLinkSource implements LinkSource {
  resolve(): Promise<LinkResolution> {
    return Promise.reject(new Error("database unreachable"));
  }
}

export interface StoredEntry {
  readonly shortCode: string;
  readonly resolution: LinkResolution;
}

export class InMemoryLinkCache implements LinkCache {
  readonly stored: StoredEntry[] = [];
  readonly #lookups: ReadonlyMap<string, CacheLookup>;

  constructor(lookups: Readonly<Record<string, CacheLookup>>) {
    this.#lookups = new Map(Object.entries(lookups));
  }

  lookup(shortCode: string): Promise<CacheLookup> {
    return Promise.resolve(this.#lookups.get(shortCode) ?? CACHE_MISS);
  }

  store(shortCode: string, resolution: LinkResolution): Promise<void> {
    this.stored.push({ shortCode, resolution });
    return Promise.resolve();
  }
}

export interface KeyValueWrite {
  readonly key: string;
  readonly value: string;
  readonly seconds: number;
}

export class InMemoryKeyValueStore implements KeyValueStore {
  readonly writes: KeyValueWrite[] = [];
  readonly #values: Map<string, string>;

  constructor(values: Readonly<Record<string, string>>) {
    this.#values = new Map(Object.entries(values));
  }

  get(key: string): Promise<string | null> {
    return Promise.resolve(this.#values.get(key) ?? null);
  }

  set(key: string, value: string, _secondsToken: "EX", seconds: number): Promise<unknown> {
    this.writes.push({ key, value, seconds });
    this.#values.set(key, value);
    return Promise.resolve("OK");
  }
}

export class FailingKeyValueStore implements KeyValueStore {
  get(): Promise<string | null> {
    return Promise.reject(new Error("connection refused"));
  }

  set(): Promise<unknown> {
    return Promise.reject(new Error("connection refused"));
  }
}

export class HangingKeyValueStore implements KeyValueStore {
  get(): Promise<string | null> {
    return new Promise(() => undefined);
  }

  set(): Promise<unknown> {
    return new Promise(() => undefined);
  }
}

export const READY_PROBE: ReadinessProbe = { isReady: () => Promise.resolve(true) };

export const UNREADY_PROBE: ReadinessProbe = { isReady: () => Promise.resolve(false) };
