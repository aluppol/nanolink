import {
  DELETED_LINK,
  type LinkResolution,
  type LinkState,
  MISSING_LINK,
  trustedLink,
  untrustedLink,
} from "../domain/linkResolution.js";

const FORMAT_VERSION = 3;

const LIFETIME_SECONDS: Readonly<Record<LinkState, number>> = {
  trusted: 300,
  untrusted: 300,
  deleted: 3600,
  missing: 30,
};

export function cacheKeyOf(shortCode: string): string {
  return `link:${shortCode}`;
}

export function cacheLifetimeSeconds(resolution: LinkResolution): number {
  return LIFETIME_SECONDS[resolution.state];
}

export function encodeCacheEntry(resolution: LinkResolution): string {
  if (resolution.state === "trusted" || resolution.state === "untrusted") {
    return JSON.stringify({
      version: FORMAT_VERSION,
      state: resolution.state,
      long_url: resolution.longUrl,
    });
  }
  return JSON.stringify({ version: FORMAT_VERSION, state: resolution.state });
}

export function decodeCacheEntry(entry: string): LinkResolution | undefined {
  const fields = parseObject(entry);
  if (fields?.version !== FORMAT_VERSION) {
    return undefined;
  }
  if (fields.state === "trusted" && typeof fields.long_url === "string") {
    return trustedLink(fields.long_url);
  }
  if (fields.state === "untrusted" && typeof fields.long_url === "string") {
    return untrustedLink(fields.long_url);
  }
  if (fields.state === "deleted") {
    return DELETED_LINK;
  }
  if (fields.state === "missing") {
    return MISSING_LINK;
  }
  return undefined;
}

function parseObject(text: string): Readonly<Record<string, unknown>> | undefined {
  try {
    const parsed: unknown = JSON.parse(text);
    return typeof parsed === "object" && parsed !== null ? { ...parsed } : undefined;
  } catch {
    return undefined;
  }
}
