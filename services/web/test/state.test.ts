import assert from "node:assert/strict";
import { test } from "node:test";
import {
  type AppState,
  createProblemCleared,
  createRejected,
  createSubmitted,
  deleteFailed,
  deleteRequested,
  deleteStarted,
  deleteSucceeded,
  draftRecorded,
  editStarted,
  firstPageLoaded,
  firstPageRequested,
  highlightCleared,
  initialState,
  type LinkRow,
  meLoaded,
  nextPageLoaded,
  pageFailed,
  saveFailed,
  saveStarted,
  saveSucceeded,
  sessionExpired,
  type Transition,
  taskQueued,
  taskSettled,
  taskTimedOut,
  toastShown,
} from "../src/model/state";
import type { Link, Me } from "../src/model/types";
import { type Case, mismatchesOf } from "./cases";

function link(id: string, longUrl = `https://example.com/${id}`): Link {
  return {
    id,
    shortCode: `code${id}`.slice(0, 6),
    shortUrl: `https://nanolink.luppol.com/${id}`,
    longUrl,
    ownerId: "u1",
    createdAt: "2026-09-24T03:00:00Z",
    updatedAt: "2026-09-24T03:00:00Z",
  };
}

const me: Me = {
  userId: "u1",
  username: "albert",
  roles: ["USER"],
  isGuest: false,
  isAdmin: false,
  dailyQuota: 200,
  createdToday: 2,
};

function page(ids: readonly string[], nextCursor: string | null = null) {
  return { links: ids.map((id) => link(id)), nextCursor };
}

function loaded(ids: readonly string[]): Transition {
  return firstPageLoaded("mine", page(ids));
}

function describeRow(row: LinkRow): string {
  return [row.link.id, row.mode, row.problem ?? "-", row.draft ?? "-", row.link.longUrl].join("|");
}

function summarize(state: AppState): Record<string, unknown> {
  return {
    pending: state.pending.map((task) =>
      task.problem === null ? task.taskId : `${task.taskId}!${task.problem}`,
    ),
    mine: state.lists.mine.rows.map(describeRow),
    all: state.lists.all.rows.map(describeRow),
    mineStatus: `${state.lists.mine.status}${state.lists.mine.hasLoaded ? "+loaded" : ""}`,
    mineCursor: state.lists.mine.nextCursor,
    highlighted: state.highlightedLinkId,
    form: `${state.createForm.isSubmitting ? "submitting" : "idle"}:${state.createForm.problem ?? "-"}:${state.createForm.acceptedSubmissions}`,
    toasts: state.toasts.map((toast) => `${toast.id}:${toast.message}`),
    createdToday: state.me?.createdToday ?? null,
    expired: state.isSessionExpired,
  };
}

function summaryAfter(
  transitions: readonly Transition[],
  keys: readonly string[],
): Record<string, unknown> {
  const summary = summarize(
    transitions.reduce((state, transition) => transition(state), initialState),
  );
  return Object.fromEntries(keys.map((key) => [key, summary[key]]));
}

const url = (id: string): string => `https://example.com/${id}`;

const CASES: readonly Case<readonly Transition[], Record<string, unknown>>[] = [
  {
    id: "first page fills my list",
    input: [firstPageRequested("mine"), firstPageLoaded("mine", page(["a", "b"], "c1"))],
    expected: {
      mine: [`a|viewing|-|-|${url("a")}`, `b|viewing|-|-|${url("b")}`],
      mineStatus: "idle+loaded",
      mineCursor: "c1",
    },
  },
  {
    id: "next page appends without duplicates",
    input: [loaded(["a", "b"]), nextPageLoaded("mine", page(["b", "c"]))],
    expected: {
      mine: [`a|viewing|-|-|${url("a")}`, `b|viewing|-|-|${url("b")}`, `c|viewing|-|-|${url("c")}`],
      mineCursor: null,
    },
  },
  {
    id: "page failure keeps the rows",
    input: [loaded(["a"]), pageFailed("mine", "down")],
    expected: { mine: [`a|viewing|-|-|${url("a")}`], mineStatus: "failed+loaded" },
  },
  {
    id: "queued task is pending and counts toward the quota",
    input: [meLoaded(me), createSubmitted(), taskQueued("t1", url("n"))],
    expected: { pending: ["t1"], createdToday: 3, form: "idle:-:1" },
  },
  {
    id: "created result replaces the pending task with a highlighted link",
    input: [
      loaded(["a"]),
      taskQueued("t1", url("x")),
      taskSettled({ taskId: "t1", status: "created", link: link("x"), failure: null }),
    ],
    expected: {
      pending: [],
      mine: [`x|viewing|-|-|${url("x")}`, `a|viewing|-|-|${url("a")}`],
      highlighted: "x",
    },
  },
  {
    id: "created result for a listed link updates it in place",
    input: [
      loaded(["a", "x"]),
      taskSettled({
        taskId: "t9",
        status: "created",
        link: link("x", "https://example.com/new"),
        failure: null,
      }),
    ],
    expected: {
      mine: [`a|viewing|-|-|${url("a")}`, "x|viewing|-|-|https://example.com/new"],
      highlighted: "x",
    },
  },
  {
    id: "failed result keeps the task with its reason",
    input: [
      taskQueued("t1", url("x")),
      taskSettled({
        taskId: "t1",
        status: "failed",
        link: null,
        failure: "Private addresses are not allowed",
      }),
    ],
    expected: { pending: ["t1!Private addresses are not allowed"] },
  },
  {
    id: "failed result without a reason uses the default",
    input: [
      taskQueued("t1", url("x")),
      taskSettled({ taskId: "t1", status: "failed", link: null, failure: null }),
    ],
    expected: { pending: ["t1!The link could not be created."] },
  },
  {
    id: "slow task is marked",
    input: [taskQueued("t1", url("x")), taskTimedOut("t1")],
    expected: { pending: ["t1!Still working on it. Refresh in a minute to see the link."] },
  },
  {
    id: "all links receive a new link only once loaded",
    input: [
      loaded(["a"]),
      taskSettled({ taskId: "t1", status: "created", link: link("x"), failure: null }),
    ],
    expected: { all: [] },
  },
  {
    id: "loaded all links receive a new link",
    input: [
      firstPageLoaded("all", page(["b"])),
      taskSettled({ taskId: "t1", status: "created", link: link("x"), failure: null }),
    ],
    expected: { all: [`x|viewing|-|-|${url("x")}`, `b|viewing|-|-|${url("b")}`] },
  },
  {
    id: "failed save keeps the draft for correction",
    input: [
      loaded(["a"]),
      editStarted("mine", "a"),
      draftRecorded("mine", "a", "https://new.example"),
      saveStarted("mine", "a"),
      saveFailed("mine", "a", "duplicate"),
    ],
    expected: { mine: [`a|editing|duplicate|https://new.example|${url("a")}`] },
  },
  {
    id: "successful save updates every list",
    input: [
      loaded(["a"]),
      firstPageLoaded("all", page(["a"])),
      editStarted("mine", "a"),
      saveSucceeded(link("a", "https://example.com/changed")),
    ],
    expected: {
      mine: ["a|viewing|-|-|https://example.com/changed"],
      all: ["a|viewing|-|-|https://example.com/changed"],
    },
  },
  {
    id: "delete removes the link everywhere",
    input: [loaded(["a", "b"]), firstPageLoaded("all", page(["a"])), deleteSucceeded("a")],
    expected: { mine: [`b|viewing|-|-|${url("b")}`], all: [] },
  },
  {
    id: "delete failure returns to viewing with the reason",
    input: [
      loaded(["a"]),
      deleteRequested("mine", "a"),
      deleteStarted("mine", "a"),
      deleteFailed("mine", "a", "oops"),
    ],
    expected: { mine: [`a|viewing|oops|-|${url("a")}`] },
  },
  {
    id: "rejected creation shows the problem",
    input: [createSubmitted(), createRejected("bad address")],
    expected: { form: "idle:bad address:0" },
  },
  {
    id: "toasts keep the newest three",
    input: [toastShown("one"), toastShown("two"), toastShown("three"), toastShown("four")],
    expected: { toasts: ["2:two", "3:three", "4:four"] },
  },
  {
    id: "session expiry stops the submission",
    input: [createSubmitted(), sessionExpired()],
    expected: { expired: true, form: "idle:-:0" },
  },
  {
    id: "highlight clears for the same link",
    input: [
      loaded([]),
      taskSettled({ taskId: "t1", status: "created", link: link("x"), failure: null }),
      highlightCleared("x"),
    ],
    expected: { highlighted: null },
  },
  {
    id: "highlight stays for another link",
    input: [
      loaded([]),
      taskSettled({ taskId: "t1", status: "created", link: link("x"), failure: null }),
      highlightCleared("y"),
    ],
    expected: { highlighted: "x" },
  },
];

const UNCHANGED_CASES: readonly Case<Transition, boolean>[] = [
  { id: "clearing a problem that is not there", input: createProblemCleared(), expected: true },
  { id: "clearing a highlight that is not there", input: highlightCleared("x"), expected: true },
  {
    id: "a queued result",
    input: taskSettled({ taskId: "t1", status: "queued", link: null, failure: null }),
    expected: true,
  },
];

test("transitions answer every case", () => {
  assert.deepEqual(
    mismatchesOf(CASES, (transitions, expected) =>
      summaryAfter(transitions, Object.keys(expected)),
    ),
    [],
  );
});

test("no-op transitions return the same state object", () => {
  assert.deepEqual(
    mismatchesOf(UNCHANGED_CASES, (transition) => transition(initialState) === initialState),
    [],
  );
});
