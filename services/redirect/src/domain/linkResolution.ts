export type LinkState = "active" | "deleted" | "missing";

export type LinkResolution =
  | { readonly state: "active"; readonly longUrl: string }
  | { readonly state: "deleted" }
  | { readonly state: "missing" };

export const DELETED_LINK: LinkResolution = { state: "deleted" };

export const MISSING_LINK: LinkResolution = { state: "missing" };

export function activeLink(longUrl: string): LinkResolution {
  return { state: "active", longUrl };
}
