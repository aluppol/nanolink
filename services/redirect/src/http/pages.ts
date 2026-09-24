import { createHash } from "node:crypto";

const PAGE_STYLE = [
  "body{margin:0;min-height:100vh;display:grid;place-items:center;",
  "font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;",
  "background:#f6f7f9;color:#1c2330}",
  "main{max-width:32rem;padding:2rem}",
  "h1{font-size:1.5rem;margin:0 0 .75rem}",
  "p{line-height:1.5;margin:0 0 1.25rem;color:#4a5263}",
  "a{color:#2b59c3}",
  "@media (prefers-color-scheme:dark){body{background:#12151c;color:#e7eaf0}",
  "p{color:#a9b1c2}a{color:#8fb0ff}}",
].join("");

export const PAGE_SECURITY_POLICY = [
  "default-src 'none'",
  `style-src 'sha256-${createHash("sha256").update(PAGE_STYLE).digest("base64")}'`,
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
].join("; ");

export const NOT_FOUND_PAGE = renderPage(
  "Link not found",
  "This link doesn't exist",
  "Check the address: a short link is six letters or digits, and letter case matters.",
);

export const GONE_PAGE = renderPage(
  "Link deleted",
  "This link was deleted",
  "Its owner removed it, so it no longer leads anywhere.",
);

export const UNAVAILABLE_PAGE = renderPage(
  "Temporarily unavailable",
  "NanoLink is temporarily unavailable",
  "The link could not be looked up right now. Please try again in a moment.",
);

export const INTERNAL_ERROR_PAGE = renderPage(
  "Something went wrong",
  "Something went wrong",
  "The error has been logged. Please try again later.",
);

function renderPage(title: string, heading: string, message: string): string {
  return [
    "<!doctype html>",
    '<html lang="en"><head><meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    '<meta name="robots" content="noindex">',
    `<title>${title} · NanoLink</title><style>${PAGE_STYLE}</style></head>`,
    `<body><main><h1>${heading}</h1><p>${message}</p>`,
    '<p><a href="/">Open NanoLink</a></p></main></body></html>',
  ].join("");
}
