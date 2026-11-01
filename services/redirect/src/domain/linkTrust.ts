import { type LinkResolution, trustedLink, untrustedLink } from "./linkResolution.js";

const SANDBOX_OWNER_ID = "sandbox";

export interface ActiveLink {
  readonly longUrl: string;
  readonly ownerId: string;
  readonly isTrusted: boolean;
}

export function resolutionOfActiveLink(link: ActiveLink): LinkResolution {
  return link.isTrusted && link.ownerId !== SANDBOX_OWNER_ID
    ? trustedLink(link.longUrl)
    : untrustedLink(link.longUrl);
}
