import ast
import io
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

MAX_FUNCTION_LINES = 30
DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def comment_violations(path: Path, source: str) -> Iterator[str]:
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            yield f"{path}:{token.start[0]}: comment"


def docstring_violations(path: Path, tree: ast.Module) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, DOCSTRING_OWNERS) and ast.get_docstring(node, clean=False) is not None:
            yield f"{path}:{getattr(node, 'lineno', 1)}: docstring"


def length_violations(path: Path, tree: ast.Module) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, FUNCTIONS) and node.end_lineno is not None:
            length = node.end_lineno - node.lineno + 1
            if length > MAX_FUNCTION_LINES:
                yield f"{path}:{node.lineno}: function {node.name} has {length} lines"


def violations(path: Path) -> Iterator[str]:
    source = path.read_text()
    tree = ast.parse(source)
    yield from comment_violations(path, source)
    yield from docstring_violations(path, tree)
    yield from length_violations(path, tree)


def main(roots: list[str]) -> int:
    files = sorted(file for root in roots for file in Path(root).rglob("*.py"))
    found = [violation for file in files for violation in violations(file)]
    for violation in found:
        sys.stdout.write(f"{violation}\n")
    sys.stdout.write(f"house rules: {len(files)} files, {len(found)} violations\n")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["src", "tests", "scripts"]))
