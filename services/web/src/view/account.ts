import { describeRole } from "../model/display";
import type { Me } from "../model/types";
import { element } from "./dom";

export class AccountView {
  private readonly container: HTMLElement;
  private lastMe: Me | null | undefined;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  render(me: Me | null): void {
    if (me === this.lastMe) {
      return;
    }
    this.lastMe = me;
    this.container.replaceChildren(...(me === null ? [] : accountParts(me)));
  }
}

function accountParts(me: Me): HTMLElement[] {
  const role = describeRole(me);
  return [
    element("span", {
      className: "account-name",
      text: me.username,
      attributes: { title: me.username },
    }),
    element("span", { className: `role-badge role-${role.toLowerCase()}`, text: role }),
    element("a", {
      className: "button button-ghost button-small",
      text: "Sign out",
      attributes: { href: "/oauth2/sign_out" },
    }),
  ];
}
