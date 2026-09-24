import { describeElapsed } from "../model/relativeTime";
import { element } from "./dom";

export function relativeTime(iso: string, now: Date): HTMLTimeElement {
  const moment = new Date(iso);
  return element("time", {
    text: describeElapsed(iso, now),
    attributes: {
      datetime: iso,
      title: Number.isNaN(moment.getTime()) ? iso : moment.toLocaleString(),
      "data-relative": "",
    },
  });
}

export function refreshRelativeTimes(root: ParentNode, now: Date): void {
  for (const time of root.querySelectorAll<HTMLTimeElement>("time[data-relative]")) {
    time.textContent = describeElapsed(time.dateTime, now);
  }
}
