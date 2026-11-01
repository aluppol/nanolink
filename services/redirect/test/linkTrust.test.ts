import assert from "node:assert/strict";
import { test } from "node:test";
import { type LinkResolution, trustedLink, untrustedLink } from "../src/domain/linkResolution.js";
import { type ActiveLink, resolutionOfActiveLink } from "../src/domain/linkTrust.js";
import { type Case, mismatchesOf } from "./support/cases.js";

const DESTINATION = "https://example.org/";
const ADMIN_ID = "0b7d4c1e-0000-4000-8000-00000000ad31";
const MEMBER_ID = "0b7d4c1e-0000-4000-8000-00000000a11c";

function link(ownerId: string, isTrusted: boolean): ActiveLink {
  return { longUrl: DESTINATION, ownerId, isTrusted };
}

const CASES: readonly Case<ActiveLink, LinkResolution>[] = [
  {
    id: "a link an admin wrote is followed at once",
    input: link(ADMIN_ID, true),
    expected: trustedLink(DESTINATION),
  },
  {
    id: "a member's link waits for the visitor's confirmation",
    input: link(MEMBER_ID, false),
    expected: untrustedLink(DESTINATION),
  },
  {
    id: "a sandbox link waits for the visitor's confirmation",
    input: link("sandbox", false),
    expected: untrustedLink(DESTINATION),
  },
  {
    id: "a sandbox link never redirects, even when marked trusted",
    input: link("sandbox", true),
    expected: untrustedLink(DESTINATION),
  },
  {
    id: "the sandbox owner id must match exactly",
    input: link("Sandbox", true),
    expected: trustedLink(DESTINATION),
  },
];

test("resolutionOfActiveLink redirects only trusted links outside the sandbox", async () => {
  assert.deepEqual(await mismatchesOf(CASES, resolutionOfActiveLink), []);
});
