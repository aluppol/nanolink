import assert from "node:assert/strict";
import { test } from "node:test";
import { confirmationPage } from "../src/http/pages.js";
import { type Case, mismatchesOf } from "./support/cases.js";

interface ShownLink {
  readonly shown: string | undefined;
  readonly href: string | undefined;
  readonly host: string | undefined;
}

function shownAs(address: string, host: string): ShownLink {
  return { shown: address, href: address, host };
}

const CASES: readonly Case<string, ShownLink>[] = [
  {
    id: "plain address is shown and linked as it is",
    input: "https://example.org/path?q=1",
    expected: shownAs("https://example.org/path?q=1", "example.org"),
  },
  {
    id: "ampersands are escaped, so a character reference stays literal",
    input: "https://example.org/?a=1&lt;b",
    expected: shownAs("https://example.org/?a=1&amp;lt;b", "example.org"),
  },
  {
    id: "a quote in the host cannot close the attribute",
    input: 'https://ex"ample.org/',
    expected: shownAs("https://ex&quot;ample.org/", "ex&quot;ample.org"),
  },
  {
    id: "apostrophes are escaped",
    input: "https://example.org/it's",
    expected: shownAs("https://example.org/it&#39;s", "example.org"),
  },
  {
    id: "markup in an opaque address is escaped",
    input: 'javascript:"<x>"',
    expected: shownAs("javascript:&quot;&lt;x&gt;&quot;", ""),
  },
  {
    id: "international host is shown in punycode",
    input: "https://exämple.org/ü",
    expected: shownAs("https://xn--exmple-cua.org/%C3%BC", "xn--exmple-cua.org"),
  },
  {
    id: "a port is part of the host",
    input: "https://example.org:8443/x",
    expected: shownAs("https://example.org:8443/x", "example.org:8443"),
  },
];

function linkShownBy(address: string): ShownLink {
  const page = confirmationPage(new URL(address));
  return {
    shown: /<code>(.*?)<\/code>/.exec(page)?.[1],
    href: /<a class="continue" href="(.*?)"/.exec(page)?.[1],
    host: /<span class="host">(.*?)<\/span>/.exec(page)?.[1],
  };
}

test("confirmationPage shows and links the normalized long URL, escaped", async () => {
  assert.deepEqual(await mismatchesOf(CASES, linkShownBy), []);
});
