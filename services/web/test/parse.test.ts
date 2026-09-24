import assert from "node:assert/strict";
import { test } from "node:test";
import {
  parseLink,
  parseLinkPage,
  parseMe,
  parseQueuedTask,
  parseTaskResult,
} from "../src/model/parse";
import type { Link } from "../src/model/types";
import { type Case, mismatchesOf } from "./cases";

const linkJson = {
  id: "66f2a1c0e4b0a1b2c3d4e5f6",
  short_code: "aB3xY9",
  short_url: "https://nanolink.luppol.com/aB3xY9",
  long_url: "https://example.com/a/very/long/path",
  owner_id: "7c1d6b1e-0000-4000-8000-000000000001",
  created_at: "2026-09-24T03:10:00Z",
  updated_at: "2026-09-24T03:12:00Z",
};

const link: Link = {
  id: "66f2a1c0e4b0a1b2c3d4e5f6",
  shortCode: "aB3xY9",
  shortUrl: "https://nanolink.luppol.com/aB3xY9",
  longUrl: "https://example.com/a/very/long/path",
  ownerId: "7c1d6b1e-0000-4000-8000-000000000001",
  createdAt: "2026-09-24T03:10:00Z",
  updatedAt: "2026-09-24T03:12:00Z",
};

const LINK_CASES: readonly Case<unknown, Link | null>[] = [
  { id: "complete link", input: linkJson, expected: link },
  {
    id: "missing updated_at falls back to created_at",
    input: { ...linkJson, updated_at: undefined },
    expected: { ...link, updatedAt: link.createdAt },
  },
  { id: "missing short_url", input: { ...linkJson, short_url: undefined }, expected: null },
  { id: "numeric id", input: { ...linkJson, id: 7 }, expected: null },
  { id: "array", input: [linkJson], expected: null },
  { id: "null", input: null, expected: null },
];

const PAGE_CASES: readonly Case<unknown, unknown>[] = [
  {
    id: "page with cursor",
    input: { links: [linkJson], next_cursor: "c1" },
    expected: { links: [link], nextCursor: "c1" },
  },
  {
    id: "last page",
    input: { links: [], next_cursor: null },
    expected: { links: [], nextCursor: null },
  },
  {
    id: "one broken link spoils the page",
    input: { links: [linkJson, { id: "x" }] },
    expected: null,
  },
  { id: "links is not a list", input: { links: "nope" }, expected: null },
];

const ME_CASES: readonly Case<unknown, unknown>[] = [
  {
    id: "full answer",
    input: {
      user_id: "u1",
      username: "albert",
      roles: ["USER", "ADMIN"],
      is_guest: false,
      is_admin: true,
      daily_quota: null,
      created_today: 4,
    },
    expected: {
      userId: "u1",
      username: "albert",
      roles: ["USER", "ADMIN"],
      isGuest: false,
      isAdmin: true,
      dailyQuota: null,
      createdToday: 4,
    },
  },
  {
    id: "flags derived from roles when absent",
    input: { user_id: "g1", roles: ["guest", 7], daily_quota: 25 },
    expected: {
      userId: "g1",
      username: "g1",
      roles: ["guest"],
      isGuest: true,
      isAdmin: false,
      dailyQuota: 25,
      createdToday: 0,
    },
  },
  {
    id: "negative quota is ignored",
    input: { user_id: "u2", daily_quota: -1 },
    expected: {
      userId: "u2",
      username: "u2",
      roles: [],
      isGuest: false,
      isAdmin: false,
      dailyQuota: null,
      createdToday: 0,
    },
  },
  { id: "no user id", input: { username: "albert" }, expected: null },
];

const TASK_CASES: readonly Case<unknown, unknown>[] = [
  {
    id: "created with link",
    input: { task_id: "t1", status: "created", link: linkJson, failure: null },
    expected: { taskId: "t1", status: "created", link, failure: null },
  },
  {
    id: "failed with reason",
    input: {
      task_id: "t2",
      status: "failed",
      link: null,
      failure: "Private addresses are not allowed",
    },
    expected: {
      taskId: "t2",
      status: "failed",
      link: null,
      failure: "Private addresses are not allowed",
    },
  },
  {
    id: "still queued",
    input: { task_id: "t3", status: "queued" },
    expected: { taskId: "t3", status: "queued", link: null, failure: null },
  },
  {
    id: "created without link is unusable",
    input: { task_id: "t4", status: "created", link: null },
    expected: null,
  },
  { id: "unknown status", input: { task_id: "t5", status: "done" }, expected: null },
  {
    id: "extra owner_id is fine",
    input: { task_id: "t6", owner_id: "u1", status: "failed", link: null, failure: null },
    expected: { taskId: "t6", status: "failed", link: null, failure: null },
  },
];

const QUEUED_CASES: readonly Case<unknown, unknown>[] = [
  { id: "accepted", input: { task_id: "t1", status: "queued" }, expected: { taskId: "t1" } },
  { id: "no task id", input: { status: "queued" }, expected: null },
];

test("parseLink answers every case", () => {
  assert.deepEqual(mismatchesOf(LINK_CASES, parseLink), []);
});

test("parseLinkPage answers every case", () => {
  assert.deepEqual(mismatchesOf(PAGE_CASES, parseLinkPage), []);
});

test("parseMe answers every case", () => {
  assert.deepEqual(mismatchesOf(ME_CASES, parseMe), []);
});

test("parseTaskResult answers every case", () => {
  assert.deepEqual(mismatchesOf(TASK_CASES, parseTaskResult), []);
});

test("parseQueuedTask answers every case", () => {
  assert.deepEqual(mismatchesOf(QUEUED_CASES, parseQueuedTask), []);
});
