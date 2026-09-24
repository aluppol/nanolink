import assert from "node:assert/strict";
import { test } from "node:test";
import { describeQuota, describeRole, displayShortUrl } from "../src/model/display";
import type { Me } from "../src/model/types";
import { type Case, mismatchesOf } from "./cases";

const user: Me = {
  userId: "7c1d",
  username: "albert",
  roles: ["USER"],
  isGuest: false,
  isAdmin: false,
  dailyQuota: 200,
  createdToday: 3,
};

const SHORT_URL_CASES: readonly Case<string, string>[] = [
  {
    id: "https",
    input: "https://nanolink.luppol.com/aB3xY9",
    expected: "nanolink.luppol.com/aB3xY9",
  },
  {
    id: "http with port",
    input: "http://127.0.0.1:8088/aB3xY9",
    expected: "127.0.0.1:8088/aB3xY9",
  },
  { id: "no scheme", input: "nanolink.luppol.com/aB3xY9", expected: "nanolink.luppol.com/aB3xY9" },
];

const ROLE_CASES: readonly Case<Me, string>[] = [
  { id: "user", input: user, expected: "User" },
  { id: "admin", input: { ...user, isAdmin: true, dailyQuota: null }, expected: "Admin" },
  { id: "guest", input: { ...user, isGuest: true }, expected: "Guest" },
  {
    id: "guest wins over admin",
    input: { ...user, isGuest: true, isAdmin: true },
    expected: "Guest",
  },
];

const QUOTA_CASES: readonly Case<Me, string>[] = [
  { id: "under the quota", input: user, expected: "3 of 200 links used today" },
  { id: "no quota", input: { ...user, dailyQuota: null }, expected: "" },
  {
    id: "quota reached",
    input: { ...user, dailyQuota: 25, createdToday: 25 },
    expected: "Daily limit reached. Try again tomorrow.",
  },
];

test("displayShortUrl answers every case", () => {
  assert.deepEqual(mismatchesOf(SHORT_URL_CASES, displayShortUrl), []);
});

test("describeRole answers every case", () => {
  assert.deepEqual(mismatchesOf(ROLE_CASES, describeRole), []);
});

test("describeQuota answers every case", () => {
  assert.deepEqual(mismatchesOf(QUOTA_CASES, describeQuota), []);
});
