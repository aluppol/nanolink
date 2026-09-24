import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { linesWithComments } from "./commentScanner.js";

const SOURCE_FILE = /\.(ts|mts|js|mjs)$/;

async function sourceFilesUnder(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { recursive: true, withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && SOURCE_FILE.test(entry.name))
    .map((entry) => join(entry.parentPath, entry.name));
}

async function commentLocationsIn(file: string): Promise<string[]> {
  const lines = linesWithComments(await readFile(file, "utf8"));
  return lines.map((line) => `${file}:${line}`);
}

const files = (await Promise.all(process.argv.slice(2).map(sourceFilesUnder))).flat();
const locations = (await Promise.all(files.map(commentLocationsIn))).flat();

if (locations.length > 0) {
  console.error(`Comments are not allowed (context.md §0):\n${locations.join("\n")}`);
  process.exit(1);
}
console.log(`No comments in ${files.length} files`);
