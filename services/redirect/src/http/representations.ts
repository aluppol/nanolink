import { GONE_PAGE, INTERNAL_ERROR_PAGE, NOT_FOUND_PAGE, UNAVAILABLE_PAGE } from "./pages.js";

export interface ErrorRepresentation {
  readonly contentType: string;
  readonly notFound: string;
  readonly gone: string;
  readonly unavailable: string;
  readonly internalError: string;
}

export const HTML_REPRESENTATION: ErrorRepresentation = {
  contentType: "text/html; charset=utf-8",
  notFound: NOT_FOUND_PAGE,
  gone: GONE_PAGE,
  unavailable: UNAVAILABLE_PAGE,
  internalError: INTERNAL_ERROR_PAGE,
};

export const JSON_REPRESENTATION: ErrorRepresentation = {
  contentType: "application/json; charset=utf-8",
  notFound: JSON.stringify({ error: "not_found" }),
  gone: JSON.stringify({ error: "gone" }),
  unavailable: JSON.stringify({ error: "unavailable" }),
  internalError: JSON.stringify({ error: "internal" }),
};

export function representationFor(acceptHeader: string | undefined): ErrorRepresentation {
  return acceptHeader?.includes("text/html") === true ? HTML_REPRESENTATION : JSON_REPRESENTATION;
}
