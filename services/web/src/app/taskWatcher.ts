import type { Api } from "../io/api";
import type { LiveStatus } from "../io/liveResults";
import type { ApiFailure } from "../model/apiFailure";
import { isTaskWaiting, taskTimedOut, waitingTaskIds } from "../model/state";
import type { TaskResult } from "../model/types";
import type { Store } from "./store";

export interface TaskOutcomeHandlers {
  settled(result: TaskResult): void;
  failed(failure: ApiFailure): void;
}

const pollIntervalMs = 2000;
const liveGraceMs = 10000;
const pollingWindowMs = 30000;

export class TaskWatcher {
  private readonly store: Store;
  private readonly api: Api;
  private readonly handlers: TaskOutcomeHandlers;
  private readonly polledTaskIds = new Set<string>();
  private liveStatus: LiveStatus = "connecting";

  constructor(store: Store, api: Api, handlers: TaskOutcomeHandlers) {
    this.store = store;
    this.api = api;
    this.handlers = handlers;
  }

  watch(taskId: string): void {
    if (this.liveStatus === "open") {
      setTimeout(() => this.startPolling(taskId), liveGraceMs);
      return;
    }
    this.startPolling(taskId);
  }

  liveStatusChanged(status: LiveStatus): void {
    this.liveStatus = status;
    if (status !== "down") {
      return;
    }
    for (const taskId of waitingTaskIds(this.store.current())) {
      this.startPolling(taskId);
    }
  }

  private startPolling(taskId: string): void {
    if (this.polledTaskIds.has(taskId) || !isTaskWaiting(this.store.current(), taskId)) {
      return;
    }
    this.polledTaskIds.add(taskId);
    this.schedulePoll(taskId, Date.now() + pollingWindowMs);
  }

  private schedulePoll(taskId: string, deadline: number): void {
    setTimeout(() => {
      void this.pollOnce(taskId, deadline);
    }, pollIntervalMs);
  }

  private async pollOnce(taskId: string, deadline: number): Promise<void> {
    if (!isTaskWaiting(this.store.current(), taskId)) {
      return;
    }
    const outcome = await this.api.fetchTask(taskId);
    if (outcome.ok && outcome.value.status !== "queued") {
      this.handlers.settled(outcome.value);
      return;
    }
    if (!outcome.ok && outcome.failure.kind === "sessionExpired") {
      this.handlers.failed(outcome.failure);
      return;
    }
    if (Date.now() >= deadline) {
      this.store.apply(taskTimedOut(taskId));
      return;
    }
    this.schedulePoll(taskId, deadline);
  }
}
