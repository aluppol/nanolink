import assert from "node:assert/strict";
import { test } from "node:test";
import { isShortCode } from "../src/domain/shortCode.js";
import { type Case, mismatchesOf } from "./support/cases.js";

const CASES: readonly Case<string, boolean>[] = [
  { id: "six mixed-case letters and digits", input: "aB3xY9", expected: true },
  { id: "six digits", input: "000000", expected: true },
  { id: "six upper-case letters", input: "ZZZZZZ", expected: true },
  { id: "five characters", input: "aB3xY", expected: false },
  { id: "seven characters", input: "aB3xY9z", expected: false },
  { id: "empty", input: "", expected: false },
  { id: "hyphen", input: "aB3-Y9", expected: false },
  { id: "underscore", input: "aB3_Y9", expected: false },
  { id: "space", input: "aB3 Y9", expected: false },
  { id: "non-ASCII letter", input: "aB3xYé", expected: false },
  { id: "trailing newline", input: "aB3xY9\n", expected: false },
  { id: "path traversal", input: "../../", expected: false },
  { id: "percent-encoded", input: "%41B3xY", expected: false },
];

test("isShortCode accepts exactly six ASCII letters or digits", async () => {
  assert.deepEqual(await mismatchesOf(CASES, isShortCode), []);
});
