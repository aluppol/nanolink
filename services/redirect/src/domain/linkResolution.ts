export type LinkState = "trusted" | "untrusted" | "deleted" | "missing";

export type LinkResolution =
  | { readonly state: "trusted"; readonly longUrl: string }
  | { readonly state: "untrusted"; readonly longUrl: string }
  | { readonly state: "deleted" }
  | { readonly state: "missing" };

export const DELETED_LINK: LinkResolution = { state: "deleted" };

export const MISSING_LINK: LinkResolution = { state: "missing" };

export function trustedLink(longUrl: string): LinkResolution {
  return { state: "trusted", longUrl };
}

export function untrustedLink(longUrl: string): LinkResolution {
  return { state: "untrusted", longUrl };
}
