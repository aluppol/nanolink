export type FailureKind =
  | "sessionExpired"
  | "forbidden"
  | "notFound"
  | "duplicateLongUrl"
  | "invalidLongUrl"
  | "quotaExceeded"
  | "unavailable"
  | "network"
  | "unexpected";

export interface ApiFailure {
  readonly status: number;
  readonly kind: FailureKind;
  readonly message: string;
}

const kindsByErrorCode = new Map<string, FailureKind>([
  ["unauthenticated", "sessionExpired"],
  ["forbidden", "forbidden"],
  ["not_found", "notFound"],
  ["duplicate_long_url", "duplicateLongUrl"],
  ["invalid_long_url", "invalidLongUrl"],
  ["quota_exceeded", "quotaExceeded"],
  ["unavailable", "unavailable"],
]);

const kindsByStatus = new Map<number, FailureKind>([
  [401, "sessionExpired"],
  [403, "forbidden"],
  [404, "notFound"],
  [409, "duplicateLongUrl"],
  [422, "invalidLongUrl"],
  [429, "quotaExceeded"],
  [502, "unavailable"],
  [503, "unavailable"],
  [504, "unavailable"],
]);

const defaultMessages: Readonly<Record<FailureKind, string>> = {
  sessionExpired: "Your session has expired.",
  forbidden: "Your account is not allowed to do that.",
  notFound: "That link no longer exists.",
  duplicateLongUrl: "You already have a short link for that URL.",
  invalidLongUrl: "That URL cannot be shortened.",
  quotaExceeded: "You have reached today's limit. Try again tomorrow.",
  unavailable: "NanoLink is temporarily unavailable. Try again in a moment.",
  network: "Can't reach NanoLink. Check your connection and try again.",
  unexpected: "Something went wrong. Try again.",
};

export function parseApiFailure(status: number, body: unknown): ApiFailure {
  const source = typeof body === "object" && body !== null ? (body as Record<string, unknown>) : {};
  const code = typeof source.error === "string" ? source.error : "";
  const kind = kindsByErrorCode.get(code) ?? kindsByStatus.get(status) ?? "unexpected";
  const hasMessage = typeof source.message === "string" && source.message.trim() !== "";
  return { status, kind, message: hasMessage ? String(source.message) : defaultMessages[kind] };
}

export function networkFailure(): ApiFailure {
  return { status: 0, kind: "network", message: defaultMessages.network };
}

export function sessionEnded(): ApiFailure {
  return { status: 401, kind: "sessionExpired", message: defaultMessages.sessionExpired };
}

export function unreadableResponse(status: number): ApiFailure {
  return {
    status,
    kind: "unexpected",
    message: "NanoLink sent a response this page could not read.",
  };
}
