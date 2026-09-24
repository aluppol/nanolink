import { copyText } from "../io/clipboard";
import { displayShortUrl } from "../model/display";
import { isWebUrl } from "../model/longUrl";
import type { LinkRow, RowMode } from "../model/state";
import type { Link, ViewName } from "../model/types";
import type { ViewContext } from "./context";
import { actionButton, element } from "./dom";
import { relativeTime } from "./relativeTimes";

export interface RowEntry {
  readonly view: ViewName;
  readonly row: LinkRow;
  readonly isHighlighted: boolean;
}

const modeClassNames: Readonly<Record<RowMode, string>> = {
  viewing: "is-viewing",
  editing: "is-editing",
  saving: "is-saving",
  confirmingDelete: "is-confirming",
  deleting: "is-deleting",
};

const copiedFeedbackMs = 1500;

export function isSameRowEntry(previous: RowEntry, next: RowEntry): boolean {
  return previous.row === next.row && previous.isHighlighted === next.isHighlighted;
}

export function renderLinkRow(entry: RowEntry, context: ViewContext): HTMLElement {
  const isEditing = entry.row.mode === "editing" || entry.row.mode === "saving";
  const highlight = entry.isHighlighted ? " is-new" : "";
  return element("li", {
    className: `link-row ${modeClassNames[entry.row.mode]}${highlight}`,
    attributes: { "data-link-id": entry.row.link.id, tabindex: "-1" },
    children: [isEditing ? editForm(entry, context) : summary(entry, context)],
  });
}

function summary(entry: RowEntry, context: ViewContext): HTMLElement {
  const { link, problem } = entry.row;
  return element("div", {
    className: "link-summary",
    children: [
      element("div", {
        className: "link-body",
        children: [
          shortLine(link, context),
          element("p", {
            className: "link-long",
            text: link.longUrl,
            attributes: { title: link.longUrl },
          }),
          metaLine(entry),
          ...problemLine(problem),
        ],
      }),
      rowActions(entry, context),
    ],
  });
}

function shortLine(link: Link, context: ViewContext): HTMLElement {
  const label = displayShortUrl(link.shortUrl);
  const target = isWebUrl(link.shortUrl)
    ? element("a", {
        className: "short-link",
        text: label,
        attributes: { href: link.shortUrl, target: "_blank", rel: "noopener noreferrer" },
      })
    : element("span", { className: "short-link", text: label });
  const copy = element("button", {
    className: "button button-ghost button-small copy-button",
    text: "Copy",
    attributes: { type: "button", "aria-label": `Copy ${label}` },
  });
  copy.addEventListener("click", () => void copyShortUrl(copy, link.shortUrl, context));
  return element("div", { className: "link-short", children: [target, copy] });
}

function metaLine(entry: RowEntry): HTMLElement {
  const created = relativeTime(entry.row.link.createdAt, new Date());
  if (entry.view === "mine") {
    return element("p", { className: "link-meta", children: ["Created ", created] });
  }
  const owner = element("span", {
    className: "owner-id",
    text: entry.row.link.ownerId,
    attributes: { title: `Owner ${entry.row.link.ownerId}` },
  });
  return element("p", { className: "link-meta", children: ["Created ", created, " by ", owner] });
}

function problemLine(problem: string | null): HTMLElement[] {
  if (problem === null) {
    return [];
  }
  return [element("p", { className: "row-problem", text: problem, attributes: { role: "alert" } })];
}

function rowActions(entry: RowEntry, context: ViewContext): HTMLElement {
  if (entry.row.mode === "confirmingDelete") {
    return deleteConfirmation(entry, context);
  }
  if (entry.row.mode === "deleting") {
    return busyNotice("Deleting…");
  }
  return idleActions(entry, context);
}

function idleActions(entry: RowEntry, context: ViewContext): HTMLElement {
  const { view } = entry;
  const linkId = entry.row.link.id;
  const remove = actionButton(
    "Delete",
    "button-ghost button-small button-danger-text",
    () => context.actions.requestDelete(view, linkId),
    view === "all" ? { "data-autofocus": "" } : {},
  );
  if (view === "all") {
    return element("div", { className: "link-actions", children: [remove] });
  }
  const edit = actionButton(
    "Edit",
    "button-secondary button-small",
    () => context.actions.startEdit(view, linkId),
    { "data-autofocus": "" },
  );
  return element("div", { className: "link-actions", children: [edit, remove] });
}

function deleteConfirmation(entry: RowEntry, context: ViewContext): HTMLElement {
  const { view } = entry;
  const linkId = entry.row.link.id;
  return element("div", {
    className: "link-actions is-confirming",
    attributes: { role: "group", "aria-label": "Confirm deletion" },
    children: [
      element("span", { className: "confirm-text", text: "Delete this link?" }),
      actionButton("Yes, delete", "button-danger button-small", () => {
        void context.actions.confirmDelete(view, linkId);
      }),
      actionButton(
        "No",
        "button-secondary button-small",
        () => context.actions.cancelDelete(view, linkId),
        {
          "data-autofocus": "",
        },
      ),
    ],
  });
}

function busyNotice(label: string): HTMLElement {
  return element("div", {
    className: "link-actions is-busy",
    children: [
      element("span", { className: "spinner", attributes: { "aria-hidden": "true" } }),
      element("span", { text: label }),
    ],
  });
}

function editForm(entry: RowEntry, context: ViewContext): HTMLElement {
  const { view } = entry;
  const { link, draft, problem, mode } = entry.row;
  const inputId = `edit-${view}-${link.id}`;
  const cancel = (): void => context.actions.cancelEdit(view, link.id);
  const input = editInput(inputId, draft ?? link.longUrl, mode === "saving", cancel);
  const form = element("form", {
    className: "edit-form",
    attributes: { novalidate: "" },
    children: [
      element("label", {
        className: "field-label",
        text: `New destination for ${displayShortUrl(link.shortUrl)}`,
        attributes: { for: inputId },
      }),
      input,
      ...problemLine(problem),
      editButtons(mode === "saving", cancel),
    ],
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void context.actions.saveEdit(view, link.id, input.value);
  });
  return form;
}

function editInput(
  id: string,
  value: string,
  isSaving: boolean,
  onEscape: () => void,
): HTMLInputElement {
  const input = element("input", {
    className: "text-input",
    attributes: { id, type: "url", inputmode: "url", autocomplete: "off", spellcheck: "false" },
  });
  input.value = value;
  input.disabled = isSaving;
  if (!isSaving) {
    input.setAttribute("data-autofocus", "");
  }
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      onEscape();
    }
  });
  return input;
}

function editButtons(isSaving: boolean, onCancel: () => void): HTMLElement {
  const save = element("button", {
    className: "button button-primary button-small",
    text: isSaving ? "Saving…" : "Save",
    attributes: { type: "submit" },
  });
  save.disabled = isSaving;
  const cancel = actionButton("Cancel", "button-ghost button-small", onCancel);
  cancel.disabled = isSaving;
  return element("div", { className: "edit-actions", children: [save, cancel] });
}

async function copyShortUrl(
  button: HTMLButtonElement,
  shortUrl: string,
  context: ViewContext,
): Promise<void> {
  if (!(await copyText(shortUrl))) {
    context.actions.showToast(
      "Copying is not available here. Select the link and copy it instead.",
    );
    return;
  }
  button.textContent = "Copied";
  button.classList.add("is-done");
  context.announce("Short link copied.");
  setTimeout(() => {
    button.textContent = "Copy";
    button.classList.remove("is-done");
  }, copiedFeedbackMs);
}
