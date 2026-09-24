import assert from "node:assert/strict";
import { test } from "node:test";
import { describeElapsed } from "../src/model/relativeTime";
import { type Case, mismatchesOf } from "./cases";

const now = new Date("2026-09-24T12:00:00.000Z");

function secondsBefore(seconds: number): string {
  return new Date(now.getTime() - seconds * 1000).toISOString();
}

const CASES: readonly Case<string, string>[] = [
  { id: "ten seconds", input: secondsBefore(10), expected: "just now" },
  { id: "clock skew into the future", input: secondsBefore(-5), expected: "just now" },
  { id: "one minute", input: secondsBefore(60), expected: "1 min ago" },
  { id: "ninety seconds rounds up", input: secondsBefore(90), expected: "2 min ago" },
  { id: "forty-four minutes", input: secondsBefore(44 * 60), expected: "44 min ago" },
  { id: "fifty minutes", input: secondsBefore(50 * 60), expected: "1 hour ago" },
  { id: "three hours", input: secondsBefore(3 * 3600), expected: "3 hours ago" },
  { id: "twenty-three hours", input: secondsBefore(23 * 3600), expected: "yesterday" },
  { id: "three days", input: secondsBefore(3 * 86400), expected: "3 days ago" },
  { id: "forty days shows the date", input: secondsBefore(40 * 86400), expected: "2026-08-15" },
  { id: "unreadable date", input: "not a date", expected: "" },
];

test("describeElapsed answers every case", () => {
  assert.deepEqual(
    mismatchesOf(CASES, (fromIso) => describeElapsed(fromIso, now)),
    [],
  );
});
