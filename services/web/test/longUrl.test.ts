import assert from "node:assert/strict";
import { test } from "node:test";
import { checkLongUrl, isWebUrl } from "../src/model/longUrl";
import { type Case, mismatchesOf } from "./cases";

const fullUrlProblem = "Enter a full URL, including https://";
const protocolProblem = "Only http and https links can be shortened.";
const base = "https://example.com/";

const CHECK_CASES: readonly Case<string, unknown>[] = [
  {
    id: "https with path and query",
    input: "https://example.com/a/b?c=d#e",
    expected: { kind: "valid", longUrl: "https://example.com/a/b?c=d#e" },
  },
  {
    id: "http is allowed",
    input: "http://example.com",
    expected: { kind: "valid", longUrl: "http://example.com" },
  },
  {
    id: "surrounding spaces are trimmed",
    input: "  https://example.com/x \n",
    expected: { kind: "valid", longUrl: "https://example.com/x" },
  },
  {
    id: "unicode host and path kept as typed",
    input: "https://bücher.example/straße",
    expected: { kind: "valid", longUrl: "https://bücher.example/straße" },
  },
  {
    id: "empty input",
    input: "   ",
    expected: { kind: "invalid", problem: "Enter a URL to shorten." },
  },
  {
    id: "missing scheme",
    input: "example.com/page",
    expected: { kind: "invalid", problem: fullUrlProblem },
  },
  {
    id: "scheme without host",
    input: "https://",
    expected: { kind: "invalid", problem: fullUrlProblem },
  },
  {
    id: "space inside the host",
    input: "https://exa mple.com",
    expected: { kind: "invalid", problem: fullUrlProblem },
  },
  {
    id: "ftp is rejected",
    input: "ftp://example.com/file",
    expected: { kind: "invalid", problem: protocolProblem },
  },
  {
    id: "javascript is rejected",
    input: "javascript:alert(1)",
    expected: { kind: "invalid", problem: protocolProblem },
  },
  {
    id: "mailto is rejected",
    input: "mailto:someone@example.com",
    expected: { kind: "invalid", problem: protocolProblem },
  },
  {
    id: "exactly 2048 characters",
    input: base + "a".repeat(2048 - base.length),
    expected: { kind: "valid", longUrl: base + "a".repeat(2048 - base.length) },
  },
  {
    id: "2049 characters",
    input: base + "a".repeat(2049 - base.length),
    expected: { kind: "invalid", problem: "That URL is longer than 2,048 characters." },
  },
];

const WEB_URL_CASES: readonly Case<string, boolean>[] = [
  { id: "https", input: "https://nanolink.luppol.com/aB3xY9", expected: true },
  { id: "http", input: "http://127.0.0.1:8088/aB3xY9", expected: true },
  { id: "javascript", input: "javascript:alert(1)", expected: false },
  { id: "relative", input: "/aB3xY9", expected: false },
];

test("checkLongUrl answers every case", () => {
  assert.deepEqual(mismatchesOf(CHECK_CASES, checkLongUrl), []);
});

test("isWebUrl answers every case", () => {
  assert.deepEqual(mismatchesOf(WEB_URL_CASES, isWebUrl), []);
});
