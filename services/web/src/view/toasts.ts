import type { Toast } from "../model/state";
import type { ViewContext } from "./context";
import { actionButton, element } from "./dom";

export function renderToast(toast: Toast, context: ViewContext): HTMLElement {
  return element("div", {
    className: "toast",
    children: [
      element("p", { className: "toast-message", text: toast.message }),
      actionButton("×", "button-ghost toast-close", () => context.actions.dismissToast(toast.id), {
        "aria-label": "Dismiss notification",
      }),
    ],
  });
}
