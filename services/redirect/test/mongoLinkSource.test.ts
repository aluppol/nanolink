import assert from "node:assert/strict";
import { test } from "node:test";
import type { Collection } from "mongodb";
import {
  type LinkRecord,
  MongoLinkSource,
  type ResolvableLinkRecord,
  resolutionOf,
} from "../src/adapters/mongoLinkSource.js";
import {
  activeLink,
  DELETED_LINK,
  type LinkResolution,
  MISSING_LINK,
} from "../src/domain/linkResolution.js";
import { type Case, mismatchesOf } from "./support/cases.js";

const CASES: readonly Case<ResolvableLinkRecord | null, LinkResolution>[] = [
  { id: "no record is missing", input: null, expected: MISSING_LINK },
  {
    id: "record without deletion is active",
    input: { long_url: "https://example.org/", deleted_at: null },
    expected: activeLink("https://example.org/"),
  },
  {
    id: "record with a deletion time is deleted",
    input: { long_url: "https://example.org/", deleted_at: new Date("2026-09-23T12:00:00Z") },
    expected: DELETED_LINK,
  },
];

interface FindOneCall {
  readonly filter: unknown;
  readonly options: unknown;
}

function recordingCollection(calls: FindOneCall[]): Collection<LinkRecord> {
  const findOne = (filter: unknown, options: unknown): Promise<ResolvableLinkRecord> => {
    calls.push({ filter, options });
    return Promise.resolve({ long_url: "https://example.org/", deleted_at: null });
  };
  return { findOne } as unknown as Collection<LinkRecord>;
}

test("resolutionOf maps a links record to a resolution", async () => {
  assert.deepEqual(await mismatchesOf(CASES, resolutionOf), []);
});

test("MongoLinkSource asks for one record by short_code with the §10 projection", async () => {
  const calls: FindOneCall[] = [];
  const resolution = await new MongoLinkSource(recordingCollection(calls)).resolve("aB3xY9");
  assert.deepEqual(resolution, activeLink("https://example.org/"));
  assert.deepEqual(calls, [
    {
      filter: { short_code: "aB3xY9" },
      options: { projection: { _id: 0, long_url: 1, deleted_at: 1 } },
    },
  ]);
});
