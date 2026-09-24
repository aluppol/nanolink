import type { PendingTask } from "../model/state";
import type { ViewContext } from "./context";
import { actionButton, element } from "./dom";

export function renderPendingTask(task: PendingTask, context: ViewContext): HTMLElement {
  return task.problem === null ? waitingTask(task) : stoppedTask(task, task.problem, context);
}

function waitingTask(task: PendingTask): HTMLElement {
  return element("li", {
    className: "pending-row",
    children: [
      element("span", { className: "spinner", attributes: { "aria-hidden": "true" } }),
      element("div", {
        className: "pending-body",
        children: [
          element("p", { className: "pending-title", text: "Shortening…" }),
          longUrlLine(task.longUrl),
        ],
      }),
    ],
  });
}

function stoppedTask(task: PendingTask, problem: string, context: ViewContext): HTMLElement {
  return element("li", {
    className: "pending-row has-problem",
    attributes: { tabindex: "-1" },
    children: [
      element("span", {
        className: "problem-mark",
        text: "!",
        attributes: { "aria-hidden": "true" },
      }),
      element("div", {
        className: "pending-body",
        children: [
          element("p", { className: "pending-title", text: "Shortening did not finish" }),
          longUrlLine(task.longUrl),
          element("p", { className: "row-problem", text: problem }),
        ],
      }),
      actionButton("Dismiss", "button-ghost button-small", () =>
        context.actions.dismissPending(task.taskId),
      ),
    ],
  });
}

function longUrlLine(longUrl: string): HTMLElement {
  return element("p", { className: "pending-url", text: longUrl, attributes: { title: longUrl } });
}
