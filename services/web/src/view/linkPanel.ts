import type { LinkList } from "../model/state";
import type { ViewName } from "../model/types";
import type { ViewContext } from "./context";
import { actionButton, element } from "./dom";
import { KeyedList } from "./keyedList";
import { isSameRowEntry, type RowEntry, renderLinkRow } from "./linkRow";

const skeletonRowCount = 3;

export class LinkPanel {
  readonly root: HTMLElement;
  private readonly view: ViewName;
  private readonly context: ViewContext;
  private readonly status = element("div", { className: "list-status" });
  private readonly rows: KeyedList<RowEntry>;
  private readonly loadMore: HTMLButtonElement;
  private readonly footerProblem = element("p", {
    className: "row-problem",
    attributes: { role: "alert" },
  });
  private lastList: LinkList | null = null;
  private lastHighlight: string | null = null;

  constructor(view: ViewName, context: ViewContext) {
    this.view = view;
    this.context = context;
    const list = element("ul", {
      className: "link-list",
      attributes: { tabindex: "-1", "aria-label": view === "mine" ? "Your links" : "All links" },
    });
    this.rows = new KeyedList(list, {
      keyOf: (entry) => entry.row.link.id,
      isSame: isSameRowEntry,
      render: (entry) => renderLinkRow(entry, context),
    });
    this.loadMore = actionButton("Load more", "button-secondary", () => {
      void context.actions.loadNextPage(view);
    });
    const footer = element("div", {
      className: "list-footer",
      children: [this.footerProblem, this.loadMore],
    });
    this.root = element("div", {
      className: "link-panel",
      attributes: { id: `panel-${view}` },
      children: [this.status, list, footer],
    });
  }

  render(list: LinkList, highlightedLinkId: string | null): void {
    if (list === this.lastList && highlightedLinkId === this.lastHighlight) {
      return;
    }
    this.lastList = list;
    this.lastHighlight = highlightedLinkId;
    this.rows.update(
      list.rows.map((row) => ({
        view: this.view,
        row,
        isHighlighted: row.link.id === highlightedLinkId,
      })),
    );
    this.status.replaceChildren(...this.statusContent(list));
    this.renderFooter(list);
  }

  private statusContent(list: LinkList): HTMLElement[] {
    if (!list.hasLoaded && list.status === "failed") {
      return [loadError(list.problem, () => void this.context.actions.loadFirstPage(this.view))];
    }
    if (!list.hasLoaded) {
      return [skeleton()];
    }
    return list.rows.length === 0 ? [emptyState(this.view)] : [];
  }

  private renderFooter(list: LinkList): void {
    const isLoadingMore = list.status === "loadingMore";
    this.loadMore.hidden = list.nextCursor === null;
    this.loadMore.disabled = isLoadingMore;
    this.loadMore.textContent = isLoadingMore ? "Loading…" : "Load more";
    const problem = list.hasLoaded && list.status === "failed" ? list.problem : null;
    this.footerProblem.textContent = problem ?? "";
    this.footerProblem.hidden = problem === null;
  }
}

function skeleton(): HTMLElement {
  const rows = Array.from({ length: skeletonRowCount }, () =>
    element("div", {
      className: "skeleton-row",
      children: [
        element("span", { className: "skeleton-line is-short" }),
        element("span", { className: "skeleton-line" }),
      ],
    }),
  );
  return element("div", {
    className: "skeleton-list",
    children: [element("p", { className: "visually-hidden", text: "Loading links…" }), ...rows],
  });
}

function emptyState(view: ViewName): HTMLElement {
  const detail =
    view === "mine"
      ? "Shorten your first URL above and it will appear here."
      : "Nobody has created a link yet.";
  return element("div", {
    className: "empty-state",
    children: [
      element("p", { className: "empty-title", text: "No links yet" }),
      element("p", { className: "empty-detail", text: detail }),
    ],
  });
}

function loadError(problem: string | null, retry: () => void): HTMLElement {
  return element("div", {
    className: "load-error",
    attributes: { role: "alert" },
    children: [
      element("p", { text: problem ?? "The links could not be loaded." }),
      actionButton("Try again", "button-secondary button-small", retry),
    ],
  });
}
