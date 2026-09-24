import type { LinkResolution } from "./linkResolution.js";

export interface LinkSource {
  resolve(shortCode: string): Promise<LinkResolution>;
}
