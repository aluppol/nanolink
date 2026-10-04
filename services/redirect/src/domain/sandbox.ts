import { activeLink, type LinkResolution, sandboxedLink } from "./linkResolution.js";

const SANDBOX_OWNER_ID = "sandbox";

export function linkOwnedBy(ownerId: string, longUrl: string): LinkResolution {
  return ownerId === SANDBOX_OWNER_ID ? sandboxedLink(longUrl) : activeLink(longUrl);
}
