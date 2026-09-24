import type { AppState, PendingTask, Toast } from "../model/state";
import type { ViewName } from "../model/types";
import { AccountView } from "./account";
import { GuestBanner, SessionBanner } from "./banners";
import type { ViewContext } from "./context";
import { CreateFormView } from "./createForm";
import { requireElement } from "./dom";
import { KeyedList } from "./keyedList";
import { LinkPanel } from "./linkPanel";
import { renderPendingTask } from "./pending";
import { ViewTabs } from "./tabs";
import { renderToast } from "./toasts";

export class AppView {
  private readonly account = new AccountView(requireElement("account", HTMLElement));
  private readonly guestBanner = new GuestBanner(requireElement("guest-banner", HTMLElement));
  private readonly sessionBanner = new SessionBanner(requireElement("session-banner", HTMLElement));
  private readonly createForm: CreateFormView;
  private readonly pending: KeyedList<PendingTask>;
  private readonly toasts: KeyedList<Toast>;
  private readonly panels: Readonly<Record<ViewName, LinkPanel>>;
  private readonly tabs: ViewTabs;

  constructor(context: ViewContext) {
    this.createForm = new CreateFormView(context);
    this.pending = new KeyedList(requireElement("pending-list", HTMLElement), {
      keyOf: (task) => task.taskId,
      isSame: (previous, next) => previous === next,
      render: (task) => renderPendingTask(task, context),
    });
    this.toasts = new KeyedList(requireElement("toasts", HTMLElement), {
      keyOf: (toast) => String(toast.id),
      isSame: (previous, next) => previous === next,
      render: (toast) => renderToast(toast, context),
    });
    this.panels = { mine: new LinkPanel("mine", context), all: new LinkPanel("all", context) };
    requireElement("link-panels", HTMLElement).append(this.panels.mine.root, this.panels.all.root);
    const tabContainer = requireElement("view-tabs", HTMLElement);
    this.tabs = new ViewTabs(
      tabContainer,
      requireElement("links-title", HTMLElement),
      this.panels,
      context,
    );
  }

  render(state: AppState): void {
    this.account.render(state.me);
    this.guestBanner.render(state.me);
    this.sessionBanner.render(state.isSessionExpired);
    this.createForm.render(state.createForm, state.me, state.isSessionExpired);
    this.pending.update(state.pending);
    this.toasts.update(state.toasts);
    this.tabs.render(state.me, state.view);
    this.panels.mine.render(state.lists.mine, state.highlightedLinkId);
    this.panels.all.render(state.lists.all, state.highlightedLinkId);
  }
}
