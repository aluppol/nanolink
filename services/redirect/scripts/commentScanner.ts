const STRING_LITERAL = /"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\[\s\S]|[^`\\])*`/g;
const COMMENT_START = /\/\/|\/\*/;

export function linesWithComments(source: string): number[] {
  const withoutStrings = source.replace(STRING_LITERAL, blankOut);
  return withoutStrings
    .split("\n")
    .flatMap((line, index) => (COMMENT_START.test(line) ? [index + 1] : []));
}

function blankOut(literal: string): string {
  return literal.replace(/[^\n]/g, " ");
}
