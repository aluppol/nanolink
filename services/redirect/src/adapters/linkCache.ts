import type { LinkResolution } from "../domain/linkResolution.js";

export type CacheLookup =
  | { readonly outcome: "hit"; readonly resolution: LinkResolution }
  | { readonly outcome: "miss" }
  | { readonly outcome: "unavailable" };

export const CACHE_MISS: CacheLookup = { outcome: "miss" };

export const CACHE_UNAVAILABLE: CacheLookup = { outcome: "unavailable" };

export function cacheHit(resolution: LinkResolution): CacheLookup {
  return { outcome: "hit", resolution };
}

export interface LinkCache {
  lookup(shortCode: string): Promise<CacheLookup>;
  store(shortCode: string, resolution: LinkResolution): Promise<void>;
}
