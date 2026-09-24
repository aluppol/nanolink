import type { Me } from "../model/types";
import { actionButton, element } from "./dom";

export class GuestBanner {
  private readonly container: HTMLElement;
  private isShown = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  render(me: Me | null): void {
    const shouldShow = me?.isGuest === true;
    if (shouldShow === this.isShown) {
      return;
    }
    this.isShown = shouldShow;
    this.container.replaceChildren(...(shouldShow ? [guestNotice()] : []));
  }
}

export class SessionBanner {
  private readonly container: HTMLElement;
  private isShown = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  render(isSessionExpired: boolean): void {
    if (isSessionExpired === this.isShown) {
      return;
    }
    this.isShown = isSessionExpired;
    this.container.replaceChildren(...(isSessionExpired ? [sessionNotice()] : []));
  }
}

function guestNotice(): HTMLElement {
  return element("div", {
    className: "banner banner-guest",
    attributes: { role: "note" },
    children: [
      element("strong", { text: "Shared demo account." }),
      " Everything created here resets every night, so feel free to try things.",
    ],
  });
}

function sessionNotice(): HTMLElement {
  return element("div", {
    className: "banner banner-alert",
    attributes: { role: "alert" },
    children: [
      element("span", { text: "Your session has expired. Reload the page to sign in again." }),
      actionButton("Reload", "button-primary button-small", () => window.location.reload()),
    ],
  });
}
