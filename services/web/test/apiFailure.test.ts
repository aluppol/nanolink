import assert from "node:assert/strict";
import { test } from "node:test";
import { type ApiFailure, parseApiFailure } from "../src/model/apiFailure";
import { type Case, mismatchesOf } from "./cases";

interface Answer {
  readonly status: number;
  readonly body: unknown;
}

const CASES: readonly Case<Answer, ApiFailure>[] = [
  {
    id: "expired token keeps the server message",
    input: { status: 401, body: { error: "unauthenticated", message: "Token expired" } },
    expected: { status: 401, kind: "sessionExpired", message: "Token expired" },
  },
  {
    id: "invalid destination",
    input: {
      status: 422,
      body: { error: "invalid_long_url", message: "Private addresses are not allowed" },
    },
    expected: { status: 422, kind: "invalidLongUrl", message: "Private addresses are not allowed" },
  },
  {
    id: "duplicate without a body falls back on the status",
    input: { status: 409, body: null },
    expected: {
      status: 409,
      kind: "duplicateLongUrl",
      message: "You already have a short link for that URL.",
    },
  },
  {
    id: "quota without a message",
    input: { status: 429, body: { error: "quota_exceeded" } },
    expected: {
      status: 429,
      kind: "quotaExceeded",
      message: "You have reached today's limit. Try again tomorrow.",
    },
  },
  {
    id: "gateway error page from nginx",
    input: { status: 502, body: null },
    expected: {
      status: 502,
      kind: "unavailable",
      message: "NanoLink is temporarily unavailable. Try again in a moment.",
    },
  },
  {
    id: "prototype key as error code",
    input: { status: 500, body: { error: "constructor" } },
    expected: { status: 500, kind: "unexpected", message: "Something went wrong. Try again." },
  },
  {
    id: "blank message is ignored",
    input: { status: 403, body: { error: "forbidden", message: "   " } },
    expected: {
      status: 403,
      kind: "forbidden",
      message: "Your account is not allowed to do that.",
    },
  },
  {
    id: "text body",
    input: { status: 418, body: "teapot" },
    expected: { status: 418, kind: "unexpected", message: "Something went wrong. Try again." },
  },
];

test("parseApiFailure answers every case", () => {
  assert.deepEqual(
    mismatchesOf(CASES, (answer) => parseApiFailure(answer.status, answer.body)),
    [],
  );
});
