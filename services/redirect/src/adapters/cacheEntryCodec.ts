import {
  activeLink,
  DELETED_LINK,
  type LinkResolution,
  type LinkState,
  MISSING_LINK,
  sandboxedLink,
} from "../domain/linkResolution.js";

const FORMAT_VERSION = 2;

const LIFETIME_SECONDS: Readonly<Record<LinkState, number>> = {
  active: 300,
  sandboxed: 300,
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
  if (resolution.state === "active" || resolution.state === "sandboxed") {
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
  if (fields.state === "active" && typeof fields.long_url === "string") {
    return activeLink(fields.long_url);
  }
  if (fields.state === "sandboxed" && typeof fields.long_url === "string") {
    return sandboxedLink(fields.long_url);
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
