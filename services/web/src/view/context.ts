import type { Actions } from "../app/actions";

export interface ViewContext {
  readonly actions: Actions;
  readonly announce: (message: string) => void;
}
