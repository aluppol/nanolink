import type { Me } from "./types";

export function displayShortUrl(shortUrl: string): string {
  if (!URL.canParse(shortUrl)) {
    return shortUrl;
  }
  const parsed = new URL(shortUrl);
  return `${parsed.host}${parsed.pathname}${parsed.search}`;
}

export function describeRole(me: Me): string {
  if (me.isGuest) {
    return "Guest";
  }
  return me.isAdmin ? "Admin" : "User";
}

export function describeQuota(me: Me): string {
  if (me.dailyQuota === null) {
    return "";
  }
  if (me.createdToday >= me.dailyQuota) {
    return "Daily limit reached. Try again tomorrow.";
  }
  return `${me.createdToday} of ${me.dailyQuota} links used today`;
}
