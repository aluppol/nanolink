import { focusPreferred } from "./dom";

export interface KeyedListSpec<Item> {
  keyOf(item: Item): string;
  isSame(previous: Item, next: Item): boolean;
  render(item: Item): HTMLElement;
}

interface RenderedItem<Item> {
  readonly item: Item;
  readonly node: HTMLElement;
}

export class KeyedList<Item> {
  private readonly container: HTMLElement;
  private readonly spec: KeyedListSpec<Item>;
  private readonly rendered = new Map<string, RenderedItem<Item>>();

  constructor(container: HTMLElement, spec: KeyedListSpec<Item>) {
    this.container = container;
    this.spec = spec;
  }

  update(items: readonly Item[]): void {
    this.removeAllExcept(new Set(items.map((item) => this.spec.keyOf(item))));
    items.forEach((item, index) => {
      this.place(this.nodeFor(this.spec.keyOf(item), item), index);
    });
  }

  private nodeFor(key: string, item: Item): HTMLElement {
    const existing = this.rendered.get(key);
    if (existing !== undefined && this.spec.isSame(existing.item, item)) {
      return existing.node;
    }
    const node = this.spec.render(item);
    if (existing !== undefined) {
      replacePreservingFocus(existing.node, node);
    }
    this.rendered.set(key, { item, node });
    return node;
  }

  private place(node: HTMLElement, index: number): void {
    const current = this.container.children.item(index);
    if (current !== node) {
      this.container.insertBefore(node, current);
    }
  }

  private removeAllExcept(keys: ReadonlySet<string>): void {
    const stale = [...this.rendered].filter(([key]) => !keys.has(key));
    const removedNodes = new Set<Element>(stale.map(([, entry]) => entry.node));
    const focusTarget = this.focusTargetWithout(removedNodes);
    for (const [key, entry] of stale) {
      entry.node.remove();
      this.rendered.delete(key);
    }
    if (focusTarget !== null) {
      focusPreferred(focusTarget);
    }
  }

  private focusTargetWithout(removedNodes: ReadonlySet<Element>): HTMLElement | null {
    const focused = [...removedNodes].find((node) => node.contains(document.activeElement));
    if (focused === undefined) {
      return null;
    }
    return (
      nextSurvivor(focused, removedNodes) ??
      previousSurvivor(focused, removedNodes) ??
      this.container
    );
  }
}

function nextSurvivor(node: Element, removedNodes: ReadonlySet<Element>): HTMLElement | null {
  let candidate = node.nextElementSibling;
  while (candidate !== null && removedNodes.has(candidate)) {
    candidate = candidate.nextElementSibling;
  }
  return candidate instanceof HTMLElement ? candidate : null;
}

function previousSurvivor(node: Element, removedNodes: ReadonlySet<Element>): HTMLElement | null {
  let candidate = node.previousElementSibling;
  while (candidate !== null && removedNodes.has(candidate)) {
    candidate = candidate.previousElementSibling;
  }
  return candidate instanceof HTMLElement ? candidate : null;
}

function replacePreservingFocus(previous: HTMLElement, next: HTMLElement): void {
  const hadFocus = previous.contains(document.activeElement);
  previous.replaceWith(next);
  if (hadFocus) {
    focusPreferred(next);
  }
}
