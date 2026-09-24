import {
  activeLink,
  DELETED_LINK,
  type LinkResolution,
  type LinkState,
  MISSING_LINK,
} from "../domain/linkResolution.js";

const LIFETIME_SECONDS: Readonly<Record<LinkState, number>> = {
  active: 300,
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
  if (resolution.state === "active") {
    return JSON.stringify({ state: "active", long_url: resolution.longUrl });
  }
  return JSON.stringify({ state: resolution.state });
}

export function decodeCacheEntry(entry: string): LinkResolution | undefined {
  const fields = parseObject(entry);
  if (fields?.state === "active" && typeof fields.long_url === "string") {
    return activeLink(fields.long_url);
  }
  if (fields?.state === "deleted") {
    return DELETED_LINK;
  }
  if (fields?.state === "missing") {
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
