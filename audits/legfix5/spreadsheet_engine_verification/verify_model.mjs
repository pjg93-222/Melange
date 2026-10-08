import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputArg, outputDirArg] = process.argv.slice(2);
if (!inputArg || !outputDirArg) {
  throw new Error("usage: node verify_model.mjs <input.xlsx> <output-dir>");
}

const inputPath = path.resolve(inputArg);
const outputDir = path.resolve(outputDirArg);
await fs.mkdir(outputDir, { recursive: true });
const sha256Bytes = (bytes) =>
  crypto.createHash("sha256").update(bytes).digest("hex");
const sha256File = async (filePath) =>
  sha256Bytes(await fs.readFile(filePath));

const hashBefore = await sha256File(inputPath);
const statBefore = await fs.stat(inputPath);
const workbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load(inputPath),
);

const checks = [
  ["Sponsor Interactions", "A1:M12"],
  ["Original Co-Sponsor Interaction", "A1:M12"],
  ["Co-Sponsor Interactions", "A1:M12"],
  ["Success Sponsor", "A1:M12"],
  ["Success Original Co-Sponsor", "A1:M12"],
  ["Legislative Score - Raw", "A1:FD12"],
  ["Legislative Score - Normalized", "A1:FD12"],
  ["Sub Layer - Raw", "A1:BB12"],
  ["Sub Layer - Normalized", "A1:BB12"],
  ["Blended Model", "A1:AB15"],
  ["Rank & Allocation", "A1:N15"],
  ["Centrality", "A1:F15"],
];
const inspections = [];
for (const [sheetId, range] of checks) {
  const result = await workbook.inspect({
    kind: "table",
    sheetId,
    range,
    include: "values,formulas",
    maxChars: 9000,
    tableMaxRows: 15,
    tableMaxCols: 160,
    tableMaxCellChars: 180,
  });
  inspections.push({
    sheet: sheetId,
    range,
    ndjson: result.ndjson,
    ndjson_sha256: sha256Bytes(Buffer.from(result.ndjson, "utf8")),
  });
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "legislation workbook formula error scan",
  maxChars: 30000,
});

const renderChecks = [
  ["Legislative Score - Raw", "A1:M20", "legislative_raw.png"],
  [
    "Legislative Score - Normalized",
    "A1:M20",
    "legislative_normalized.png",
  ],
  ["Sub Layer - Raw", "A1:BB18", "sub_layer_raw.png"],
  ["Blended Model", "A1:AB18", "blended_model.png"],
  ["Rank & Allocation", "A1:N18", "rank_allocation.png"],
];
const renders = [];
for (const [sheetName, range, fileName] of renderChecks) {
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 1,
    format: "png",
  });
  const bytes = new Uint8Array(await preview.arrayBuffer());
  const outputPath = path.join(outputDir, fileName);
  await fs.writeFile(outputPath, bytes);
  renders.push({
    sheet: sheetName,
    range,
    path: fileName,
    size: bytes.byteLength,
    sha256: sha256Bytes(bytes),
  });
}

const hashAfter = await sha256File(inputPath);
const statAfter = await fs.stat(inputPath);
const errorText = errors.ndjson || "";
const errorRecords = errorText
  .split(/\r?\n/)
  .filter((line) => line.trim())
  .map((line) => {
    try {
      return JSON.parse(line);
    } catch {
      return { kind: "invalid-ndjson", raw: line };
    }
  });
const errorMatches = errorRecords.filter(
  (record) =>
    record.kind !== "notice" &&
    record.kind !== "summary" &&
    !(
      typeof record.message === "string" &&
      /matched\s+0\s+entries/i.test(record.message)
    ),
);
const inspectionTables = Object.fromEntries(
  inspections.map((item) => {
    const first = (item.ndjson || "")
      .split(/\r?\n/)
      .find((line) => line.trim());
    if (!first) return [item.sheet, null];
    try {
      return [item.sheet, JSON.parse(first)];
    } catch {
      return [item.sheet, null];
    }
  }),
);
const subLayerSample =
  inspectionTables["Sub Layer - Raw"]?.values || [];
const subLayerSampleData = subLayerSample.slice(3);
const subLayerCriticalSampleCells = subLayerSampleData.flatMap((row) =>
  (Array.isArray(row) ? row : []).slice(2, 21),
);
const subLayerCriticalSampleNonNumeric =
  subLayerCriticalSampleCells.filter(
    (value) => typeof value !== "number" || !Number.isFinite(value),
  ).length;
const receipt = {
  schema: "legislation-spreadsheet-model-verification-v1",
  status:
    hashBefore === hashAfter &&
    statBefore.size === statAfter.size &&
    errorMatches.length === 0 &&
    subLayerCriticalSampleNonNumeric === 0 &&
    renders.every((item) => item.size > 0)
      ? "PASS"
      : "BLOCKED",
  engine: "@oai/artifact-tool",
  production_written: false,
  workbook_edited: false,
  input: {
    path: inputPath,
    size: statBefore.size,
    sha256: hashBefore,
    unchanged_after_verification:
      hashBefore === hashAfter && statBefore.size === statAfter.size,
  },
  formula_error_scan: {
    pattern: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    record_count: errorMatches.length,
    raw_record_count: errorRecords.length,
    notices_ignored: errorRecords.length - errorMatches.length,
    ndjson: errorText,
  },
  critical_numeric_sample: {
    sheet: "Sub Layer - Raw",
    range: "C4:U12",
    expected_numeric_cells: subLayerCriticalSampleCells.length,
    non_numeric_cells: subLayerCriticalSampleNonNumeric,
    passed: subLayerCriticalSampleNonNumeric === 0,
    reason:
      "Legislation-dependent sublayer cells must be materialized numeric values; blanks or unsupported formula results are not accepted.",
  },
  inspections,
  renders,
};
const receiptPath = path.join(outputDir, "model_verification_receipt.json");
await fs.writeFile(
  receiptPath,
  `${JSON.stringify(receipt, null, 2)}\n`,
  "utf8",
);
console.log(
  JSON.stringify({
    status: receipt.status,
    formula_error_records: errorMatches.length,
    sublayer_non_numeric_sample_cells:
      subLayerCriticalSampleNonNumeric,
    inspection_count: inspections.length,
    render_count: renders.length,
    receipt: receiptPath,
  }),
);
if (receipt.status !== "PASS") process.exitCode = 2;
