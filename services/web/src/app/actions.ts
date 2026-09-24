import type { Api, Outcome } from "../io/api";
import type { LiveStatus } from "../io/liveResults";
import type { ApiFailure } from "../model/apiFailure";
import { displayShortUrl } from "../model/display";
import { checkLongUrl } from "../model/longUrl";
import {
  createAbandoned,
  createProblemCleared,
  createRejected,
  createSubmitted,
  deleteCancelled,
  deleteFailed,
  deleteRequested,
  deleteStarted,
  deleteSucceeded,
  draftRecorded,
  editCancelled,
  editStarted,
  firstPageLoaded,
  firstPageRequested,
  highlightCleared,
  meLoaded,
  nextPageLoaded,
  nextPageRequested,
  pageFailed,
  pendingDismissed,
  saveFailed,
  saveStarted,
  saveSucceeded,
  sessionExpired,
  taskQueued,
  taskSettled,
  toastDismissed,
  toastShown,
  viewSelected,
} from "../model/state";
import type { LinkPage, TaskResult, ViewName } from "../model/types";
import type { Store } from "./store";
import { TaskWatcher } from "./taskWatcher";

const toastLifetimeMs = 8000;
const highlightLifetimeMs = 4000;
const creationFieldFailures = new Set(["invalidLongUrl", "quotaExceeded", "duplicateLongUrl"]);

export class Actions {
  private readonly store: Store;
  private readonly api: Api;
  private readonly announce: (message: string) => void;
  private readonly watcher: TaskWatcher;

  constructor(store: Store, api: Api, announce: (message: string) => void) {
    this.store = store;
    this.api = api;
    this.announce = announce;
    this.watcher = new TaskWatcher(store, api, {
      settled: (result) => this.settleTask(result),
      failed: (failure) => this.reportFailure(failure),
    });
  }

  async loadMe(): Promise<void> {
    const outcome = await this.api.fetchMe();
    if (outcome.ok) {
      this.store.apply(meLoaded(outcome.value));
      return;
    }
    this.reportFailure(outcome.failure);
  }

  async loadFirstPage(view: ViewName): Promise<void> {
    this.store.apply(firstPageRequested(view));
    const outcome = await this.fetchLinks(view, null);
    if (outcome.ok) {
      this.store.apply(firstPageLoaded(view, outcome.value));
      return;
    }
    this.failPage(view, outcome.failure);
  }

  async loadNextPage(view: ViewName): Promise<void> {
    const list = this.store.current().lists[view];
    if (list.nextCursor === null || list.status === "loadingMore") {
      return;
    }
    this.store.apply(nextPageRequested(view));
    const outcome = await this.fetchLinks(view, list.nextCursor);
    if (outcome.ok) {
      this.store.apply(nextPageLoaded(view, outcome.value));
      return;
    }
    this.failPage(view, outcome.failure);
  }

  selectView(view: ViewName): void {
    this.store.apply(viewSelected(view));
    const list = this.store.current().lists[view];
    if (!list.hasLoaded && list.status === "idle") {
      void this.loadFirstPage(view);
    }
  }

  async submitLongUrl(input: string): Promise<void> {
    const check = checkLongUrl(input);
    if (check.kind === "invalid") {
      this.store.apply(createRejected(check.problem));
      return;
    }
    this.store.apply(createSubmitted());
    const outcome = await this.api.queueLink(check.longUrl);
    if (outcome.ok) {
      this.store.apply(taskQueued(outcome.value.taskId, check.longUrl));
      this.watcher.watch(outcome.value.taskId);
      return;
    }
    this.rejectCreation(outcome.failure);
  }

  clearCreateProblem(): void {
    this.store.apply(createProblemCleared());
  }

  startEdit(view: ViewName, linkId: string): void {
    this.store.apply(editStarted(view, linkId));
  }

  cancelEdit(view: ViewName, linkId: string): void {
    this.store.apply(editCancelled(view, linkId));
  }

  async saveEdit(view: ViewName, linkId: string, input: string): Promise<void> {
    this.store.apply(draftRecorded(view, linkId, input));
    const check = checkLongUrl(input);
    if (check.kind === "invalid") {
      this.store.apply(saveFailed(view, linkId, check.problem));
      return;
    }
    this.store.apply(saveStarted(view, linkId));
    const outcome = await this.api.changeLinkTarget(linkId, check.longUrl);
    if (outcome.ok) {
      this.store.apply(saveSucceeded(outcome.value));
      this.announce("Destination updated.");
      return;
    }
    this.store.apply(saveFailed(view, linkId, outcome.failure.message));
    this.expireSessionOn(outcome.failure);
  }

  requestDelete(view: ViewName, linkId: string): void {
    this.store.apply(deleteRequested(view, linkId));
  }

  cancelDelete(view: ViewName, linkId: string): void {
    this.store.apply(deleteCancelled(view, linkId));
  }

  async confirmDelete(view: ViewName, linkId: string): Promise<void> {
    this.store.apply(deleteStarted(view, linkId));
    const outcome =
      view === "mine" ? await this.api.deleteMyLink(linkId) : await this.api.deleteAnyLink(linkId);
    if (outcome.ok || outcome.failure.kind === "notFound") {
      this.store.apply(deleteSucceeded(linkId));
      this.announce("Link deleted.");
      return;
    }
    this.store.apply(deleteFailed(view, linkId, outcome.failure.message));
    this.expireSessionOn(outcome.failure);
  }

  dismissPending(taskId: string): void {
    this.store.apply(pendingDismissed(taskId));
  }

  dismissToast(toastId: number): void {
    this.store.apply(toastDismissed(toastId));
  }

  showToast(message: string): void {
    const toastId = this.store.current().nextToastId;
    this.store.apply(toastShown(message));
    setTimeout(() => this.store.apply(toastDismissed(toastId)), toastLifetimeMs);
  }

  settleTask(result: TaskResult): void {
    this.store.apply(taskSettled(result));
    if (result.status !== "created" || result.link === null) {
      return;
    }
    const linkId = result.link.id;
    this.announce(`Short link ready: ${displayShortUrl(result.link.shortUrl)}`);
    setTimeout(() => this.store.apply(highlightCleared(linkId)), highlightLifetimeMs);
  }

  liveStatusChanged(status: LiveStatus): void {
    this.watcher.liveStatusChanged(status);
  }

  private fetchLinks(view: ViewName, cursor: string | null): Promise<Outcome<LinkPage>> {
    return view === "mine" ? this.api.fetchMyLinks(cursor) : this.api.fetchAllLinks(cursor);
  }

  private failPage(view: ViewName, failure: ApiFailure): void {
    this.store.apply(pageFailed(view, failure.message));
    this.expireSessionOn(failure);
  }

  private rejectCreation(failure: ApiFailure): void {
    if (creationFieldFailures.has(failure.kind)) {
      this.store.apply(createRejected(failure.message));
      return;
    }
    this.store.apply(createAbandoned());
    this.reportFailure(failure);
  }

  private reportFailure(failure: ApiFailure): void {
    if (failure.kind === "sessionExpired") {
      this.store.apply(sessionExpired());
      return;
    }
    this.showToast(failure.message);
  }

  private expireSessionOn(failure: ApiFailure): void {
    if (failure.kind === "sessionExpired") {
      this.store.apply(sessionExpired());
    }
  }
}
