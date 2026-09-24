import type { Me, ViewName } from "../model/types";
import type { ViewContext } from "./context";
import { element } from "./dom";
import type { LinkPanel } from "./linkPanel";

const viewNames: readonly ViewName[] = ["mine", "all"];
const tabLabels: Readonly<Record<ViewName, string>> = { mine: "My links", all: "All links" };

export class ViewTabs {
  private readonly container: HTMLElement;
  private readonly title: HTMLElement;
  private readonly panels: Readonly<Record<ViewName, LinkPanel>>;
  private readonly context: ViewContext;
  private lastKey = "";

  constructor(
    container: HTMLElement,
    title: HTMLElement,
    panels: Readonly<Record<ViewName, LinkPanel>>,
    context: ViewContext,
  ) {
    this.container = container;
    this.title = title;
    this.panels = panels;
    this.context = context;
  }

  render(me: Me | null, view: ViewName): void {
    const isAdmin = me?.isAdmin === true;
    const key = `${isAdmin}:${view}`;
    if (key === this.lastKey) {
      return;
    }
    this.lastKey = key;
    const hadFocus = this.container.contains(document.activeElement);
    this.title.textContent = isAdmin ? "Links" : "Your links";
    this.container.replaceChildren(...(isAdmin ? [this.tabList(view)] : []));
    this.showPanels(isAdmin, view);
    if (hadFocus) {
      document.getElementById(`tab-${view}`)?.focus();
    }
  }

  private tabList(view: ViewName): HTMLElement {
    const list = element("div", {
      className: "tab-list",
      attributes: { role: "tablist", "aria-label": "Link views" },
      children: viewNames.map((name) => this.tab(name, name === view)),
    });
    list.addEventListener("keydown", (event) => this.switchWithArrows(event, view));
    return list;
  }

  private tab(name: ViewName, isSelected: boolean): HTMLButtonElement {
    return element("button", {
      className: "tab",
      text: tabLabels[name],
      attributes: {
        type: "button",
        role: "tab",
        id: `tab-${name}`,
        "aria-selected": String(isSelected),
        "aria-controls": `panel-${name}`,
        tabindex: isSelected ? "0" : "-1",
      },
      listeners: { click: () => this.context.actions.selectView(name) },
    });
  }

  private switchWithArrows(event: KeyboardEvent, view: ViewName): void {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
      return;
    }
    event.preventDefault();
    this.context.actions.selectView(view === "mine" ? "all" : "mine");
  }

  private showPanels(isAdmin: boolean, view: ViewName): void {
    for (const name of viewNames) {
      const panel = this.panels[name].root;
      panel.hidden = name !== view;
      if (isAdmin) {
        panel.setAttribute("role", "tabpanel");
        panel.setAttribute("aria-labelledby", `tab-${name}`);
      }
    }
  }
}
