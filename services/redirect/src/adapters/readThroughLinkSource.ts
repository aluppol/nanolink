import type { LinkResolution } from "../domain/linkResolution.js";
import type { LinkSource } from "../domain/linkSource.js";
import type { LinkCache } from "./linkCache.js";

export class ReadThroughLinkSource implements LinkSource {
  readonly #cache: LinkCache;
  readonly #origin: LinkSource;

  constructor(cache: LinkCache, origin: LinkSource) {
    this.#cache = cache;
    this.#origin = origin;
  }

  async resolve(shortCode: string): Promise<LinkResolution> {
    const lookup = await this.#cache.lookup(shortCode);
    if (lookup.outcome === "hit") {
      return lookup.resolution;
    }
    const resolution = await this.#origin.resolve(shortCode);
    if (lookup.outcome === "miss") {
      await this.#cache.store(shortCode, resolution);
    }
    return resolution;
  }
}
