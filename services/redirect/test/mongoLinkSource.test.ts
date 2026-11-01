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
  DELETED_LINK,
  type LinkResolution,
  MISSING_LINK,
  trustedLink,
  untrustedLink,
} from "../src/domain/linkResolution.js";
import { type Case, mismatchesOf } from "./support/cases.js";

const ADMIN_ID = "0b7d4c1e-0000-4000-8000-00000000ad31";
const MEMBER_ID = "0b7d4c1e-0000-4000-8000-00000000a11c";
const DESTINATION = "https://example.org/";
const DELETION_TIME = new Date("2026-09-23T12:00:00Z");

function record(fields: Partial<ResolvableLinkRecord>): ResolvableLinkRecord {
  return { long_url: DESTINATION, owner_id: MEMBER_ID, deleted_at: null, ...fields };
}

const CASES: readonly Case<ResolvableLinkRecord | null, LinkResolution>[] = [
  { id: "no record is missing", input: null, expected: MISSING_LINK },
  {
    id: "a record marked trusted redirects",
    input: record({ owner_id: ADMIN_ID, trusted: true }),
    expected: trustedLink(DESTINATION),
  },
  {
    id: "a record marked untrusted asks first",
    input: record({ trusted: false }),
    expected: untrustedLink(DESTINATION),
  },
  {
    id: "a record written before the trusted field existed asks first",
    input: record({}),
    expected: untrustedLink(DESTINATION),
  },
  {
    id: "a trusted field that is not the boolean true asks first",
    input: { ...record({}), trusted: "true" } as unknown as ResolvableLinkRecord,
    expected: untrustedLink(DESTINATION),
  },
  {
    id: "a sandbox record asks first",
    input: record({ owner_id: "sandbox", trusted: false }),
    expected: untrustedLink(DESTINATION),
  },
  {
    id: "a sandbox record asks first even when marked trusted",
    input: record({ owner_id: "sandbox", trusted: true }),
    expected: untrustedLink(DESTINATION),
  },
  {
    id: "a record with a deletion time is deleted",
    input: record({ deleted_at: DELETION_TIME }),
    expected: DELETED_LINK,
  },
  {
    id: "a deleted trusted record is deleted",
    input: record({ owner_id: ADMIN_ID, trusted: true, deleted_at: DELETION_TIME }),
    expected: DELETED_LINK,
  },
  {
    id: "a deleted sandbox record is deleted",
    input: record({ owner_id: "sandbox", deleted_at: DELETION_TIME }),
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
    return Promise.resolve(record({ owner_id: ADMIN_ID, trusted: true }));
  };
  return { findOne } as unknown as Collection<LinkRecord>;
}

test("resolutionOf maps a links record to a resolution", async () => {
  assert.deepEqual(await mismatchesOf(CASES, resolutionOf), []);
});

test("MongoLinkSource asks for one record by short_code with the §10 projection", async () => {
  const calls: FindOneCall[] = [];
  const resolution = await new MongoLinkSource(recordingCollection(calls)).resolve("aB3xY9");
  assert.deepEqual(resolution, trustedLink(DESTINATION));
  assert.deepEqual(calls, [
    {
      filter: { short_code: "aB3xY9" },
      options: { projection: { _id: 0, long_url: 1, owner_id: 1, trusted: 1, deleted_at: 1 } },
    },
  ]);
});
