export const maximumLongUrlLength = 2048;

export type LongUrlCheck =
  | { readonly kind: "valid"; readonly longUrl: string }
  | { readonly kind: "invalid"; readonly problem: string };

const webProtocols = new Set(["http:", "https:"]);

export function checkLongUrl(input: string): LongUrlCheck {
  const candidate = input.trim();
  if (candidate === "") {
    return invalid("Enter a URL to shorten.");
  }
  if (candidate.length > maximumLongUrlLength) {
    return invalid("That URL is longer than 2,048 characters.");
  }
  const parsed = URL.canParse(candidate) ? new URL(candidate) : null;
  if (parsed === null) {
    return invalid("Enter a full URL, including https://");
  }
  if (!webProtocols.has(parsed.protocol)) {
    return invalid("Only http and https links can be shortened.");
  }
  if (parsed.hostname === "") {
    return invalid("Enter a full URL, including https://");
  }
  return { kind: "valid", longUrl: candidate };
}

export function isWebUrl(value: string): boolean {
  return URL.canParse(value) && webProtocols.has(new URL(value).protocol);
}

function invalid(problem: string): LongUrlCheck {
  return { kind: "invalid", problem };
}
