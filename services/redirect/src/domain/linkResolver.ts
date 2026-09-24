import { type LinkResolution, MISSING_LINK } from "./linkResolution.js";
import type { LinkSource } from "./linkSource.js";
import { isShortCode } from "./shortCode.js";

export class LinkResolver {
  readonly #source: LinkSource;

  constructor(source: LinkSource) {
    this.#source = source;
  }

  async resolve(candidate: string): Promise<LinkResolution> {
    if (!isShortCode(candidate)) {
      return MISSING_LINK;
    }
    return this.#source.resolve(candidate);
  }
}
