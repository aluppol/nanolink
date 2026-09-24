import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { findComments } from "./comments";

const checkedExtensions = [".ts", ".css", ".html", ".svg"];

async function listCheckedFiles(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { recursive: true, withFileTypes: true });
  return entries
    .filter(
      (entry) => entry.isFile() && checkedExtensions.some((ending) => entry.name.endsWith(ending)),
    )
    .map((entry) => join(entry.parentPath, entry.name));
}

async function reportComments(directories: readonly string[]): Promise<void> {
  const files = (await Promise.all(directories.map(listCheckedFiles))).flat();
  const sources = await Promise.all(
    files.map(async (file) => ({ file, text: await readFile(file, "utf8") })),
  );
  const findings = sources.flatMap((source) => findComments(source.file, source.text));
  for (const finding of findings) {
    process.stderr.write(`${finding.file}:${finding.line}: ${finding.text}\n`);
  }
  if (findings.length > 0) {
    process.stderr.write(`${findings.length} comment(s) found; the house rule is no comments.\n`);
    process.exitCode = 1;
    return;
  }
  process.stdout.write(`No comments in ${files.length} files.\n`);
}

await reportComments(process.argv.slice(2));
