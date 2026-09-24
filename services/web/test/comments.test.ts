import assert from "node:assert/strict";
import { test } from "node:test";
import { findComments } from "../scripts/comments";
import { type Case, mismatchesOf } from "./cases";

const slash = "/";
const star = "*";

const CASES: readonly Case<string, readonly number[]>[] = [
  { id: "plain code", input: "const total = price * count / 2;", expected: [] },
  { id: "line comment", input: `const total = 1; ${slash}${slash} explain`, expected: [1] },
  { id: "block comment", input: `${slash}${star} explain ${star}${slash}`, expected: [1] },
  { id: "html comment", input: "<!-- explain -->", expected: [1] },
  {
    id: "url in double quotes",
    input: 'const home = "https://github.com/aluppol/nanolink";',
    expected: [],
  },
  { id: "url in single quotes", input: "fetch('https://example.com/a');", expected: [] },
  {
    id: "url in a template literal",
    input: "const link = `https://example.com/page`;",
    expected: [],
  },
  {
    id: "url in an html attribute",
    input: '<a href="https://github.com/aluppol/nanolink">source</a>',
    expected: [],
  },
  {
    id: "css comment",
    input: `.card { color: red; } ${slash}${star} why ${star}${slash}`,
    expected: [1],
  },
  {
    id: "second line only",
    input: `const a = 1;\n${slash}${slash} note\nconst b = 2;`,
    expected: [2],
  },
];

test("findComments answers every case", () => {
  assert.deepEqual(
    mismatchesOf(CASES, (source) =>
      findComments("sample.ts", source).map((finding) => finding.line),
    ),
    [],
  );
});
