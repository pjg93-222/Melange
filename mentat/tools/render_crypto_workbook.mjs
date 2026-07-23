import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const runtimeNodeModules = process.env.MENTAT_NODE_MODULES ?? path.join(
  os.homedir(), ".cache", "codex-runtimes", "codex-primary-runtime",
  "dependencies", "node", "node_modules",
);
const require = createRequire(import.meta.url);
const artifactToolEntry = require.resolve("@oai/artifact-tool", { paths: [runtimeNodeModules] });
const { FileBlob, SpreadsheetFile } = await import(pathToFileURL(artifactToolEntry).href);

const [workbookPath, jsonPath, outputDirectory] = process.argv.slice(2);
if (!workbookPath || !jsonPath || !outputDirectory) {
  throw new Error("usage: render_crypto_workbook.mjs <workbook.xlsx> <crypto-data.json> <output-dir>");
}

const payload = JSON.parse(await fs.readFile(jsonPath, "utf8"));
const companyViewName = (company) => `${company} View`.slice(0, 31);
const previews = process.env.MENTAT_RENDER_MASTER_ONLY === "1" ? [
  ["Master Overview", "A1:Q45", "Master_Overview_Summary"],
  ["Master Overview", "R1:BJ18", "Master_Overview_Recipient_Channels"],
  ["Master Overview", "BK1:CE18", "Master_Overview_Contributor_Roles"],
] : [
  ["Master Overview", "A1:Q45"],
  ["Crypto Spending Overview", "A1:J52"],
  ...payload.cycles.map((cycle) => [`${cycle.label} Summary`, "A1:S35"]),
  ["Company List", "A1:O36"],
  ...payload.companies.map((company) => [companyViewName(company), "A1:S35"]),
  ["Employee List", "A1:S30"],
  ["Recipient List", "A1:AD30"],
  ["Beneficiary Summary", "A1:V30"],
  ["PAC & Candidate Map", "A1:S30"],
  ["Downstream Activity", "A1:AB25"],
  ["Beneficiary Bridge", "A1:V25"],
  ...payload.cycles.map((cycle) => [cycle.label, "A1:AI20"]),
  ["Cycle Exceptions", "A1:AI20"],
];

await fs.mkdir(outputDirectory, { recursive: true });
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
const rendered = [];
for (const [sheetName, range, fileToken] of previews) {
  const preview = await workbook.render({ sheetName, range, scale: 0.65, format: "png" });
  const fileName = `${(fileToken ?? sheetName).replaceAll(/[^A-Za-z0-9]+/g, "_")}.png`;
  const target = path.join(outputDirectory, fileName);
  await fs.writeFile(target, new Uint8Array(await preview.arrayBuffer()));
  rendered.push({ sheet: sheetName, range, file: target });
}
await fs.writeFile(
  path.join(outputDirectory, "render_manifest.json"),
  JSON.stringify({ workbook: workbookPath, sheet_count: rendered.length, rendered }, null, 2),
  "utf8",
);
console.log(`RENDERED_SHEETS=${rendered.length}`);
