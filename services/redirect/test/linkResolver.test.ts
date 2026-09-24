import assert from "node:assert/strict";
import { test } from "node:test";
import { activeLink, DELETED_LINK, type LinkResolution } from "../src/domain/linkResolution.js";
import { LinkResolver } from "../src/domain/linkResolver.js";
import { type Case, mismatchesOf } from "./support/cases.js";
import { InMemoryLinkSource } from "./support/fakes.js";

interface Outcome {
  readonly resolution: LinkResolution;
  readonly askedSourceFor: readonly string[];
}

const LINKS = {
  aB3xY9: activeLink("https://example.org/"),
  dE1eT3: DELETED_LINK,
};

const CASES: readonly Case<string, Outcome>[] = [
  {
    id: "active code is answered by the source",
    input: "aB3xY9",
    expected: { resolution: activeLink("https://example.org/"), askedSourceFor: ["aB3xY9"] },
  },
  {
    id: "deleted code is answered by the source",
    input: "dE1eT3",
    expected: { resolution: DELETED_LINK, askedSourceFor: ["dE1eT3"] },
  },
  {
    id: "unknown valid code is missing after asking the source",
    input: "zZ9zZ9",
    expected: { resolution: { state: "missing" }, askedSourceFor: ["zZ9zZ9"] },
  },
  {
    id: "malformed code is missing without asking the source",
    input: "not-a-code",
    expected: { resolution: { state: "missing" }, askedSourceFor: [] },
  },
];

async function resolveWithFreshSource(candidate: string): Promise<Outcome> {
  const source = new InMemoryLinkSource(LINKS);
  const resolution = await new LinkResolver(source).resolve(candidate);
  return { resolution, askedSourceFor: source.requestedCodes };
}

test("LinkResolver validates the code before asking the source", async () => {
  assert.deepEqual(await mismatchesOf(CASES, resolveWithFreshSource), []);
});
