import { describeQuota } from "../model/display";
import type { CreateForm } from "../model/state";
import type { Me } from "../model/types";
import type { ViewContext } from "./context";
import { requireElement } from "./dom";

export class CreateFormView {
  private readonly input = requireElement("long-url", HTMLInputElement);
  private readonly submit = requireElement("create-submit", HTMLButtonElement);
  private readonly problem = requireElement("long-url-problem", HTMLElement);
  private readonly quota = requireElement("quota-hint", HTMLElement);
  private seenSubmissions = 0;

  constructor(context: ViewContext) {
    const form = requireElement("create-form", HTMLFormElement);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void context.actions.submitLongUrl(this.input.value);
    });
    this.input.addEventListener("input", () => context.actions.clearCreateProblem());
  }

  render(form: CreateForm, me: Me | null, isSessionExpired: boolean): void {
    this.submit.disabled = form.isSubmitting || isSessionExpired;
    this.submit.textContent = form.isSubmitting ? "Queuing…" : "Shorten";
    this.problem.textContent = form.problem ?? "";
    this.problem.hidden = form.problem === null;
    this.input.setAttribute("aria-invalid", String(form.problem !== null));
    this.quota.textContent = me === null ? "" : describeQuota(me);
    this.clearAfterAcceptance(form.acceptedSubmissions);
  }

  private clearAfterAcceptance(acceptedSubmissions: number): void {
    if (acceptedSubmissions === this.seenSubmissions) {
      return;
    }
    this.seenSubmissions = acceptedSubmissions;
    this.input.value = "";
    this.input.focus();
  }
}
