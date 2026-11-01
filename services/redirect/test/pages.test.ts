import assert from "node:assert/strict";
import { test } from "node:test";
import { confirmationPage } from "../src/http/pages.js";
import { type Case, mismatchesOf } from "./support/cases.js";

const CONTINUE_REL = "noopener noreferrer nofollow ugc";

interface ShownLink {
  readonly headingHost: string | undefined;
  readonly shown: string | undefined;
  readonly href: string | undefined;
  readonly rel: string | undefined;
  readonly buttonHost: string | undefined;
}

function shownAs(address: string, host: string): ShownLink {
  return { headingHost: host, shown: address, href: address, rel: CONTINUE_REL, buttonHost: host };
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
    headingHost: /<h1>You are leaving NanoLink for <span class="host">(.*?)<\/span><\/h1>/.exec(
      page,
    )?.[1],
    shown: /<code>(.*?)<\/code>/.exec(page)?.[1],
    href: /<a class="continue" href="(.*?)"/.exec(page)?.[1],
    rel: /<a class="continue" href=".*?" rel="(.*?)">/.exec(page)?.[1],
    buttonHost: /Continue to <span class="host">(.*?)<\/span><\/a>/.exec(page)?.[1],
  };
}

test("confirmationPage names the host and shows and links the normalized long URL, escaped", async () => {
  assert.deepEqual(await mismatchesOf(CASES, linkShownBy), []);
});

test("confirmationPage never moves on by itself", () => {
  const page = confirmationPage(new URL("https://example.org/path"));
  assert.deepEqual(
    page.match(/<script|<form|<iframe|<object|<embed|http-equiv|onload|onclick/gi),
    null,
  );
  assert.equal(page.match(/href="https:\/\/example\.org\/path"/g)?.length, 1);
});
