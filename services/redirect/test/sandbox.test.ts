import assert from "node:assert/strict";
import { test } from "node:test";
import { activeLink, type LinkResolution, sandboxedLink } from "../src/domain/linkResolution.js";
import { linkOwnedBy } from "../src/domain/sandbox.js";
import { type Case, mismatchesOf } from "./support/cases.js";

const DESTINATION = "https://example.org/";
const MEMBER_ID = "0b7d4c1e-0000-4000-8000-00000000a11c";

const CASES: readonly Case<string, LinkResolution>[] = [
  {
    id: "a member's link is followed at once",
    input: MEMBER_ID,
    expected: activeLink(DESTINATION),
  },
  {
    id: "a sandbox link waits for the visitor's confirmation",
    input: "sandbox",
    expected: sandboxedLink(DESTINATION),
  },
  { id: "the owner id must match exactly", input: "Sandbox", expected: activeLink(DESTINATION) },
];

test("linkOwnedBy asks for confirmation only for links in the shared sandbox", async () => {
  const ownedBy = (ownerId: string): LinkResolution => linkOwnedBy(ownerId, DESTINATION);
  assert.deepEqual(await mismatchesOf(CASES, ownedBy), []);
});
