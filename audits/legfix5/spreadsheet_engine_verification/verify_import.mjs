import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputArg, outputArg] = process.argv.slice(2);
if (!inputArg || !outputArg) {
  throw new Error("usage: node verify_import.mjs <input.xlsx> <receipt.json>");
}

const inputPath = path.resolve(inputArg);
const outputPath = path.resolve(outputArg);
const sha256 = async (filePath) => {
  const bytes = await fs.readFile(filePath);
  return crypto.createHash("sha256").update(bytes).digest("hex");
};

const inputHashBefore = await sha256(inputPath);
const inputStatBefore = await fs.stat(inputPath);
const workbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load(inputPath),
);
const sheetNames = workbook.worksheets.items.map((sheet) => sheet.name);
const required = [
  "Rank & Allocation",
  "Blended Model",
  "Legislative Score - Raw",
  "Legislative Score - Normalized",
  "Sub Layer - Raw",
  "Sub Layer - Normalized",
  "Press Release - Raw",
  "Press Release - Normalized",
];
const missing = required.filter((name) => !sheetNames.includes(name));
const sheetInspection = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 30000,
});
const inputHashAfter = await sha256(inputPath);
const inputStatAfter = await fs.stat(inputPath);
const receipt = {
  schema: "legislation-spreadsheet-engine-import-verification-v1",
  status:
    missing.length === 0 &&
    inputHashBefore === inputHashAfter &&
    inputStatBefore.size === inputStatAfter.size
      ? "PASS"
      : "BLOCKED",
  engine: "@oai/artifact-tool",
  import_completed: true,
  production_written: false,
  workbook_edited: false,
  input: {
    path: inputPath,
    size: inputStatBefore.size,
    sha256: inputHashBefore,
    unchanged_after_import:
      inputHashBefore === inputHashAfter &&
      inputStatBefore.size === inputStatAfter.size,
  },
  required_sheets: required,
  missing_required_sheets: missing,
  sheet_count: sheetNames.length,
  sheet_names: sheetNames,
  sheet_inspection: sheetInspection.ndjson,
};
await fs.writeFile(
  outputPath,
  `${JSON.stringify(receipt, null, 2)}\n`,
  "utf8",
);
console.log(
  JSON.stringify({
    status: receipt.status,
    sheet_count: receipt.sheet_count,
    missing_required_sheets: missing,
    receipt: outputPath,
  }),
);
if (receipt.status !== "PASS") process.exitCode = 2;
