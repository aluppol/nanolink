import assert from "node:assert/strict";
import { test } from "node:test";
import { linesWithComments } from "../scripts/commentScanner.js";
import { type Case, mismatchesOf } from "./support/cases.js";

const SLASHES = "/".repeat(2);
const BLOCK_OPEN = "/".concat("*");
const BLOCK_CLOSE = "*".concat("/");
const HOST_PLACEHOLDER = "$".concat("{host}");

const CASES: readonly Case<string, number[]>[] = [
  { id: "plain code", input: "const answer = 42;\n", expected: [] },
  { id: "line comment", input: `const a = 1;\n${SLASHES} note\n`, expected: [2] },
  { id: "trailing line comment", input: `const a = 1; ${SLASHES} note\n`, expected: [1] },
  {
    id: "block comment",
    input: `${BLOCK_OPEN} note ${BLOCK_CLOSE}\nconst a = 1;\n`,
    expected: [1],
  },
  { id: "URL in double quotes", input: 'const url = "https://example.org";\n', expected: [] },
  { id: "URL in single quotes", input: "const url = 'https://example.org';\n", expected: [] },
  {
    id: "URL in a template",
    input: `const url = \`https://${HOST_PLACEHOLDER}/x\`;\n`,
    expected: [],
  },
  {
    id: "glob in a string",
    input: `const glob = "test/${"*".repeat(2)}${BLOCK_OPEN}.test.ts";\n`,
    expected: [],
  },
  { id: "escaped quote inside a string", input: 'const s = "a\\"b"; const t = 1;\n', expected: [] },
  {
    id: "multi-line template keeps line numbers",
    input: "const t = `a\nb`;\nconst c = 1;\n",
    expected: [],
  },
  {
    id: "comment after a multi-line template",
    input: `const t = \`a\nb\`;\n${SLASHES} note\n`,
    expected: [3],
  },
];

test("linesWithComments finds comments and ignores comment-like text inside strings", async () => {
  assert.deepEqual(await mismatchesOf(CASES, linesWithComments), []);
});
