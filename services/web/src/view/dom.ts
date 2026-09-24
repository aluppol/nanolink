export interface ElementOptions {
  readonly className?: string;
  readonly text?: string;
  readonly attributes?: Readonly<Record<string, string>>;
  readonly listeners?: Readonly<Record<string, EventListener>>;
  readonly children?: readonly (Node | string)[];
}

export function element<Tag extends keyof HTMLElementTagNameMap>(
  tag: Tag,
  options: ElementOptions = {},
): HTMLElementTagNameMap[Tag] {
  const node = document.createElement(tag);
  if (options.className !== undefined) {
    node.className = options.className;
  }
  if (options.text !== undefined) {
    node.textContent = options.text;
  }
  for (const [name, value] of Object.entries(options.attributes ?? {})) {
    node.setAttribute(name, value);
  }
  for (const [type, listener] of Object.entries(options.listeners ?? {})) {
    node.addEventListener(type, listener);
  }
  node.append(...(options.children ?? []));
  return node;
}

export function actionButton(
  label: string,
  className: string,
  onClick: () => void,
  attributes: Readonly<Record<string, string>> = {},
): HTMLButtonElement {
  return element("button", {
    className: `button ${className}`,
    text: label,
    attributes: { type: "button", ...attributes },
    listeners: { click: () => onClick() },
  });
}

export function requireElement<Kind extends HTMLElement>(id: string, kind: new () => Kind): Kind {
  const found = document.getElementById(id);
  if (!(found instanceof kind)) {
    throw new Error(`The page is missing the element #${id}.`);
  }
  return found;
}

export function focusPreferred(root: HTMLElement): void {
  const target = root.querySelector<HTMLElement>("[data-autofocus]") ?? root;
  target.focus();
  if (target instanceof HTMLInputElement) {
    target.select();
  }
}
