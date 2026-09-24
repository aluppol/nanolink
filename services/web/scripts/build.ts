import { createHash } from "node:crypto";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { basename } from "node:path";
import { build, type Metafile } from "esbuild";
import { fillTemplate } from "./template";

const outputDirectory = "dist";
const assetDirectory = `${outputDirectory}/assets`;
const pages = [
  { template: "src/pages/index.html", output: `${outputDirectory}/index.html` },
  { template: "src/pages/404.html", output: `${outputDirectory}/404.html` },
  { template: "src/pages/50x.html", output: `${outputDirectory}/50x.html` },
];

async function buildSite(): Promise<void> {
  await rm(outputDirectory, { recursive: true, force: true });
  await mkdir(assetDirectory, { recursive: true });
  const bundled = await bundleSources();
  const logo = await publishHashed("src/assets/logo.svg");
  const assetNames = { ...bundled, "logo.svg": logo };
  for (const page of pages) {
    const template = await readFile(page.template, "utf8");
    await writeFile(page.output, fillTemplate(template, assetNames));
  }
  process.stdout.write(
    `Built ${Object.values(assetNames).join(", ")} and ${pages.length} pages.\n`,
  );
}

async function bundleSources(): Promise<Record<"app.js" | "app.css", string>> {
  const result = await build({
    entryPoints: ["src/main.ts", "src/styles/app.css"],
    bundle: true,
    minify: true,
    sourcemap: "linked",
    format: "esm",
    target: ["es2022"],
    entryNames: "[name]-[hash]",
    outdir: assetDirectory,
    metafile: true,
    legalComments: "none",
    logLevel: "warning",
  });
  return {
    "app.js": entryOutput(result.metafile, ".js"),
    "app.css": entryOutput(result.metafile, ".css"),
  };
}

function entryOutput(metafile: Metafile, extension: string): string {
  const match = Object.entries(metafile.outputs).find(
    ([path, output]) => path.endsWith(extension) && output.entryPoint !== undefined,
  );
  if (match === undefined) {
    throw new Error(`esbuild produced no ${extension} entry file.`);
  }
  return basename(match[0]);
}

async function publishHashed(sourcePath: string): Promise<string> {
  const content = await readFile(sourcePath);
  const digest = createHash("sha256").update(content).digest("hex").slice(0, 10);
  const [name, extension] = basename(sourcePath).split(".");
  const fileName = `${name}-${digest}.${extension}`;
  await writeFile(`${assetDirectory}/${fileName}`, content);
  return fileName;
}

await buildSite();
