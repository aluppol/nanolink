import { parseTaskResult } from "../model/parse";
import type { TaskResult } from "../model/types";

export type LiveStatus = "connecting" | "open" | "down";

export interface LiveResultsListener {
  resultArrived(result: TaskResult): void;
  statusChanged(status: LiveStatus): void;
}

const reconnectDelayMs = 15000;

export function connectLiveResults(url: string, listener: LiveResultsListener): void {
  const source = new EventSource(url);
  source.addEventListener("open", () => listener.statusChanged("open"));
  source.addEventListener("link-result", (event) => forwardResult(event, listener));
  source.addEventListener("error", () => {
    if (source.readyState !== EventSource.CLOSED) {
      listener.statusChanged("connecting");
      return;
    }
    listener.statusChanged("down");
    setTimeout(() => connectLiveResults(url, listener), reconnectDelayMs);
  });
}

function forwardResult(event: Event, listener: LiveResultsListener): void {
  if (!(event instanceof MessageEvent) || typeof event.data !== "string") {
    return;
  }
  const result = parseTaskResult(readJson(event.data));
  if (result !== null) {
    listener.resultArrived(result);
  }
}

function readJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
