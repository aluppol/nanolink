export interface CommentFinding {
  readonly file: string;
  readonly line: number;
  readonly text: string;
}

const commentMarkers = ["/" + "/", "/" + "*", "<" + "!--"];
const quotedText = /"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`/g;

export function findComments(file: string, source: string): readonly CommentFinding[] {
  return source
    .split("\n")
    .flatMap((text, index) =>
      hasComment(text) ? [{ file, line: index + 1, text: text.trim() }] : [],
    );
}

function hasComment(line: string): boolean {
  const code = line.replace(quotedText, '""');
  return commentMarkers.some((marker) => code.includes(marker));
}
