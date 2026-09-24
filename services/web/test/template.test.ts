import assert from "node:assert/strict";
import { test } from "node:test";
import { fillTemplate } from "../scripts/template";
import { type Case, errorMessageOf, mismatchesOf } from "./cases";

const names = {
  "app.js": "main-AB12CD.js",
  "app.css": "app-EF34GH.css",
  "logo.svg": "logo-0a1b2c3d4e.svg",
};

const CASES: readonly Case<string, string>[] = [
  {
    id: "one placeholder",
    input: '<script src="/assets/{{app.js}}"></script>',
    expected: '<script src="/assets/main-AB12CD.js"></script>',
  },
  {
    id: "repeated placeholder",
    input: "{{logo.svg}} {{logo.svg}}",
    expected: "logo-0a1b2c3d4e.svg logo-0a1b2c3d4e.svg",
  },
  { id: "no placeholders", input: "<p>plain</p>", expected: "<p>plain</p>" },
  {
    id: "unknown placeholder",
    input: "{{app.map}}",
    expected: "The template needs a value for {{app.map}}.",
  },
  {
    id: "prototype key is not a value",
    input: "{{constructor}}",
    expected: "The template needs a value for {{constructor}}.",
  },
];

test("fillTemplate answers every case", () => {
  assert.deepEqual(
    mismatchesOf(CASES, (template) => {
      const message = errorMessageOf(() => fillTemplate(template, names));
      return message === "no error" ? fillTemplate(template, names) : message;
    }),
    [],
  );
});
