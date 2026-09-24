import { Actions } from "./app/actions";
import { createStore, type Store } from "./app/store";
import { httpApi } from "./io/api";
import { connectLiveResults } from "./io/liveResults";
import { initialState } from "./model/state";
import { createAnnouncer } from "./view/announcer";
import { AppView } from "./view/appView";
import { requireElement } from "./view/dom";
import { refreshRelativeTimes } from "./view/relativeTimes";

const relativeTimeRefreshMs = 30000;

function start(): void {
  const store = createStore(initialState);
  const announce = createAnnouncer(requireElement("live-region", HTMLElement));
  const actions = new Actions(store, httpApi, announce);
  const view = new AppView({ actions, announce });
  store.subscribe(renderAfterCurrentTask(view, store));
  view.render(store.current());
  connectLiveResults("/api/notifications", {
    resultArrived: (result) => actions.settleTask(result),
    statusChanged: (status) => actions.liveStatusChanged(status),
  });
  void actions.loadMe();
  void actions.loadFirstPage("mine");
  setInterval(() => refreshRelativeTimes(document, new Date()), relativeTimeRefreshMs);
}

function renderAfterCurrentTask(view: AppView, store: Store): () => void {
  let isScheduled = false;
  return () => {
    if (isScheduled) {
      return;
    }
    isScheduled = true;
    queueMicrotask(() => {
      isScheduled = false;
      view.render(store.current());
    });
  };
}

start();
