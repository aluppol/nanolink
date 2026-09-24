const placeholderPattern = /\{\{([^{}]+)\}\}/g;

export function fillTemplate(template: string, values: Readonly<Record<string, string>>): string {
  return template.replace(placeholderPattern, (_placeholder, name: string) => {
    if (!Object.hasOwn(values, name)) {
      throw new Error(`The template needs a value for {{${name}}}.`);
    }
    return String(values[name]);
  });
}
