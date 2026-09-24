import type { AppState, Transition } from "../model/state";

export interface Store {
  current(): AppState;
  apply(transition: Transition): void;
  subscribe(listener: (state: AppState) => void): void;
}

export function createStore(initial: AppState): Store {
  let state = initial;
  const listeners: Array<(state: AppState) => void> = [];
  return {
    current: () => state,
    apply: (transition) => {
      const next = transition(state);
      if (next === state) {
        return;
      }
      state = next;
      for (const listener of listeners) {
        listener(state);
      }
    },
    subscribe: (listener) => {
      listeners.push(listener);
    },
  };
}
