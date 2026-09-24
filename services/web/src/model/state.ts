import type { Link, LinkPage, Me, TaskResult, ViewName } from "./types";

export type RowMode = "viewing" | "editing" | "saving" | "confirmingDelete" | "deleting";
export type ListStatus = "idle" | "loadingFirst" | "loadingMore" | "failed";

export interface LinkRow {
  readonly link: Link;
  readonly mode: RowMode;
  readonly problem: string | null;
  readonly draft: string | null;
}

export interface LinkList {
  readonly rows: readonly LinkRow[];
  readonly nextCursor: string | null;
  readonly status: ListStatus;
  readonly hasLoaded: boolean;
  readonly problem: string | null;
}

export interface PendingTask {
  readonly taskId: string;
  readonly longUrl: string;
  readonly problem: string | null;
}

export interface Toast {
  readonly id: number;
  readonly message: string;
}

export interface CreateForm {
  readonly isSubmitting: boolean;
  readonly problem: string | null;
  readonly acceptedSubmissions: number;
}

export interface AppState {
  readonly me: Me | null;
  readonly view: ViewName;
  readonly lists: Readonly<Record<ViewName, LinkList>>;
  readonly pending: readonly PendingTask[];
  readonly createForm: CreateForm;
  readonly highlightedLinkId: string | null;
  readonly toasts: readonly Toast[];
  readonly nextToastId: number;
  readonly isSessionExpired: boolean;
}

export type Transition = (state: AppState) => AppState;

const emptyList: LinkList = {
  rows: [],
  nextCursor: null,
  status: "idle",
  hasLoaded: false,
  problem: null,
};

const visibleToastLimit = 3;
const failedTaskProblem = "The link could not be created.";
const slowTaskProblem = "Still working on it. Refresh in a minute to see the link.";

export const initialState: AppState = {
  me: null,
  view: "mine",
  lists: { mine: emptyList, all: emptyList },
  pending: [],
  createForm: { isSubmitting: false, problem: null, acceptedSubmissions: 0 },
  highlightedLinkId: null,
  toasts: [],
  nextToastId: 1,
  isSessionExpired: false,
};

export function meLoaded(me: Me): Transition {
  return (state) => ({ ...state, me });
}

export function viewSelected(view: ViewName): Transition {
  return (state) => ({ ...state, view });
}

export function firstPageRequested(view: ViewName): Transition {
  return (state) =>
    withList(state, view, (list) => ({ ...list, status: "loadingFirst", problem: null }));
}

export function nextPageRequested(view: ViewName): Transition {
  return (state) =>
    withList(state, view, (list) => ({ ...list, status: "loadingMore", problem: null }));
}

export function firstPageLoaded(view: ViewName, page: LinkPage): Transition {
  return (state) =>
    withList(state, view, () => ({
      rows: page.links.map(viewingRow),
      nextCursor: page.nextCursor,
      status: "idle",
      hasLoaded: true,
      problem: null,
    }));
}

export function nextPageLoaded(view: ViewName, page: LinkPage): Transition {
  return (state) =>
    withList(state, view, (list) => ({
      ...list,
      rows: appendUnseen(list.rows, page.links),
      nextCursor: page.nextCursor,
      status: "idle",
      problem: null,
    }));
}

export function pageFailed(view: ViewName, problem: string): Transition {
  return (state) => withList(state, view, (list) => ({ ...list, status: "failed", problem }));
}

export function createSubmitted(): Transition {
  return (state) => withCreateForm(state, { isSubmitting: true, problem: null });
}

export function createRejected(problem: string): Transition {
  return (state) => withCreateForm(state, { isSubmitting: false, problem });
}

export function createAbandoned(): Transition {
  return (state) => withCreateForm(state, { isSubmitting: false, problem: null });
}

export function createProblemCleared(): Transition {
  return (state) =>
    state.createForm.problem === null ? state : withCreateForm(state, { problem: null });
}

export function taskQueued(taskId: string, longUrl: string): Transition {
  return (state) => ({
    ...state,
    createForm: {
      isSubmitting: false,
      problem: null,
      acceptedSubmissions: state.createForm.acceptedSubmissions + 1,
    },
    pending: [{ taskId, longUrl, problem: null }, ...withoutTask(state.pending, taskId)],
    me: state.me === null ? null : { ...state.me, createdToday: state.me.createdToday + 1 },
  });
}

export function taskSettled(result: TaskResult): Transition {
  return (state) => {
    if (result.status === "created" && result.link !== null) {
      return linkArrived(
        { ...state, pending: withoutTask(state.pending, result.taskId) },
        result.link,
      );
    }
    if (result.status === "failed") {
      return withTaskProblem(state, result.taskId, result.failure ?? failedTaskProblem);
    }
    return state;
  };
}

export function taskTimedOut(taskId: string): Transition {
  return (state) => withTaskProblem(state, taskId, slowTaskProblem);
}

export function pendingDismissed(taskId: string): Transition {
  return (state) => ({ ...state, pending: withoutTask(state.pending, taskId) });
}

export function editStarted(view: ViewName, linkId: string): Transition {
  return (state) => withRow(state, view, linkId, { mode: "editing", problem: null, draft: null });
}

export function editCancelled(view: ViewName, linkId: string): Transition {
  return (state) => withRow(state, view, linkId, { mode: "viewing", problem: null, draft: null });
}

export function draftRecorded(view: ViewName, linkId: string, draft: string): Transition {
  return (state) => withRow(state, view, linkId, { draft });
}

export function saveStarted(view: ViewName, linkId: string): Transition {
  return (state) => withRow(state, view, linkId, { mode: "saving", problem: null });
}

export function saveFailed(view: ViewName, linkId: string, problem: string): Transition {
  return (state) => withRow(state, view, linkId, { mode: "editing", problem });
}

export function saveSucceeded(link: Link): Transition {
  return (state) => withEveryList(state, (list) => replaceLink(list, link));
}

export function deleteRequested(view: ViewName, linkId: string): Transition {
  return (state) => withRow(state, view, linkId, { mode: "confirmingDelete", problem: null });
}

export function deleteCancelled(view: ViewName, linkId: string): Transition {
  return (state) => withRow(state, view, linkId, { mode: "viewing", problem: null });
}

export function deleteStarted(view: ViewName, linkId: string): Transition {
  return (state) => withRow(state, view, linkId, { mode: "deleting", problem: null });
}

export function deleteFailed(view: ViewName, linkId: string, problem: string): Transition {
  return (state) => withRow(state, view, linkId, { mode: "viewing", problem });
}

export function deleteSucceeded(linkId: string): Transition {
  return (state) =>
    withEveryList(state, (list) => ({
      ...list,
      rows: list.rows.filter((row) => row.link.id !== linkId),
    }));
}

export function toastShown(message: string): Transition {
  return (state) => ({
    ...state,
    toasts: [...state.toasts, { id: state.nextToastId, message }].slice(-visibleToastLimit),
    nextToastId: state.nextToastId + 1,
  });
}

export function toastDismissed(toastId: number): Transition {
  return (state) => ({ ...state, toasts: state.toasts.filter((toast) => toast.id !== toastId) });
}

export function sessionExpired(): Transition {
  return (state) => ({
    ...withCreateForm(state, { isSubmitting: false, problem: null }),
    isSessionExpired: true,
  });
}

export function highlightCleared(linkId: string): Transition {
  return (state) =>
    state.highlightedLinkId === linkId ? { ...state, highlightedLinkId: null } : state;
}

export function isTaskWaiting(state: AppState, taskId: string): boolean {
  return state.pending.some((task) => task.taskId === taskId && task.problem === null);
}

export function waitingTaskIds(state: AppState): readonly string[] {
  return state.pending.filter((task) => task.problem === null).map((task) => task.taskId);
}

function viewingRow(link: Link): LinkRow {
  return { link, mode: "viewing", problem: null, draft: null };
}

function withList(state: AppState, view: ViewName, change: (list: LinkList) => LinkList): AppState {
  return { ...state, lists: { ...state.lists, [view]: change(state.lists[view]) } };
}

function withEveryList(state: AppState, change: (list: LinkList) => LinkList): AppState {
  return withList(withList(state, "mine", change), "all", change);
}

function withRow(
  state: AppState,
  view: ViewName,
  linkId: string,
  change: Partial<Pick<LinkRow, "mode" | "problem" | "draft">>,
): AppState {
  return withList(state, view, (list) => ({
    ...list,
    rows: list.rows.map((row) => (row.link.id === linkId ? { ...row, ...change } : row)),
  }));
}

function withCreateForm(state: AppState, change: Partial<CreateForm>): AppState {
  return { ...state, createForm: { ...state.createForm, ...change } };
}

function withoutTask(pending: readonly PendingTask[], taskId: string): readonly PendingTask[] {
  return pending.filter((task) => task.taskId !== taskId);
}

function withTaskProblem(state: AppState, taskId: string, problem: string): AppState {
  return {
    ...state,
    pending: state.pending.map((task) => (task.taskId === taskId ? { ...task, problem } : task)),
  };
}

function linkArrived(state: AppState, link: Link): AppState {
  const placed = withList(state, "mine", (list) => placeLink(list, link));
  const everywhere = state.lists.all.hasLoaded
    ? withList(placed, "all", (list) => placeLink(list, link))
    : placed;
  return { ...everywhere, highlightedLinkId: link.id };
}

function placeLink(list: LinkList, link: Link): LinkList {
  const isListed = list.rows.some((row) => row.link.id === link.id);
  return isListed ? replaceLink(list, link) : { ...list, rows: [viewingRow(link), ...list.rows] };
}

function replaceLink(list: LinkList, link: Link): LinkList {
  return {
    ...list,
    rows: list.rows.map((row) => (row.link.id === link.id ? viewingRow(link) : row)),
  };
}

function appendUnseen(rows: readonly LinkRow[], links: readonly Link[]): readonly LinkRow[] {
  const seen = new Set(rows.map((row) => row.link.id));
  return [...rows, ...links.filter((link) => !seen.has(link.id)).map(viewingRow)];
}
