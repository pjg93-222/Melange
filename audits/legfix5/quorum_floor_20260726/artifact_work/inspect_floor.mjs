import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, outputDir] = process.argv.slice(2);
if (!inputPath || !outputDir) {
  throw new Error("usage: inspect_floor.mjs <input.xlsx> <output-dir>");
}

await fs.mkdir(outputDir, { recursive: true });
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheetInspection = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 8000,
});

const sheets = [];
for (let index = 0; ; index += 1) {
  let sheet;
  try {
    sheet = workbook.worksheets.getItemAt(index);
  } catch {
    break;
  }
  if (!sheet) break;
  const used = sheet.getUsedRange(true);
  const values = used ? used.values : [];
  sheets.push({
    index,
    name: sheet.name,
    row_count: values.length,
    column_count: values.reduce(
      (maximum, row) => Math.max(maximum, row.length),
      0,
    ),
    values,
  });
  const preview = await workbook.render({
    sheetName: sheet.name,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, `sheet_${String(index + 1).padStart(2, "0")}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

await fs.writeFile(
  path.join(outputDir, "workbook_values.json"),
  `${JSON.stringify(
    {
      input_path: path.resolve(inputPath),
      sheet_inspection_ndjson: sheetInspection.ndjson,
      sheets,
    },
    null,
    2,
  )}\n`,
  "utf8",
);

if (sheets.length !== 1 || sheets[0].row_count < 2) {
  throw new Error("expected one non-empty Quorum floor worksheet");
}
const [headers, ...dataRows] = sheets[0].values;
const headerIndex = new Map(headers.map((header, index) => [header, index]));
const requiredHeaders = [
  "Quorum ID",
  "Label",
  "Title",
  "Bill Number",
  "Session",
  "Stance",
  "Issues",
  "Source Link",
];
for (const header of requiredHeaders) {
  if (!headerIndex.has(header)) {
    throw new Error(`missing required Quorum floor column: ${header}`);
  }
}
const get = (row, header) => row[headerIndex.get(header)] ?? null;
const typeMap = new Map([
  ["house-bill", "hr"],
  ["senate-bill", "s"],
  ["house-resolution", "hres"],
  ["senate-resolution", "sres"],
  ["house-joint-resolution", "hjres"],
  ["senate-joint-resolution", "sjres"],
  ["house-concurrent-resolution", "hconres"],
  ["senate-concurrent-resolution", "sconres"],
]);
const floorRows = dataRows
  .filter((row) => row.some((value) => value !== null && value !== ""))
  .map((row, index) => {
    const sourceLink = String(get(row, "Source Link") ?? "").trim();
    const match = sourceLink.match(
      /^https:\/\/www\.congress\.gov\/bill\/(\d+)(?:st|nd|rd|th)-congress\/([^/]+)\/(\d+)\/?$/i,
    );
    if (!match || !typeMap.has(match[2].toLowerCase())) {
      throw new Error(
        `row ${index + 2} has an invalid Congress.gov bill URL: ${sourceLink}`,
      );
    }
    const congress = Number(match[1]);
    const type = typeMap.get(match[2].toLowerCase());
    const number = Number(match[3]);
    const session = String(get(row, "Session") ?? "");
    if (!session.includes(`${congress}th Congress`) &&
        !session.includes(`${congress}st Congress`) &&
        !session.includes(`${congress}nd Congress`) &&
        !session.includes(`${congress}rd Congress`)) {
      throw new Error(
        `row ${index + 2} session does not match its Congress.gov URL`,
      );
    }
    return {
      source_row: index + 2,
      quorum_id: String(get(row, "Quorum ID") ?? ""),
      identifier: `${congress}:${type}:${number}`,
      congress,
      type,
      number,
      label: get(row, "Label"),
      title: get(row, "Title"),
      introduced_date: get(row, "Introduced Date"),
      session,
      stance: get(row, "Stance"),
      issues: get(row, "Issues"),
      source_link: sourceLink,
    };
  });
const byIdentifier = new Map();
for (const row of floorRows) {
  const existing = byIdentifier.get(row.identifier) ?? [];
  existing.push(row.source_row);
  byIdentifier.set(row.identifier, existing);
}
const duplicateIdentifiers = [...byIdentifier.entries()]
  .filter(([, rows]) => rows.length > 1)
  .map(([identifier, rows]) => ({ identifier, source_rows: rows }));
const inputBytes = await fs.readFile(inputPath);
const sha256 = (value) =>
  createHash("sha256").update(value).digest("hex");
const uniqueIdentifiers = [...byIdentifier.keys()].sort();
const floorManifest = {
  schema: "acu-legislation-quorum-recall-floor-v1",
  status: "FROZEN_FLOOR_NOT_PRIMARY",
  created_at: new Date().toISOString(),
  collection_policy: {
    primary_instrument: "Congress.gov Advanced Search - Legislation",
    quorum_used_as_primary: false,
    quorum_used_as_recall_floor: true,
    floor_semantics:
      "Every valid in-scope floor identifier must appear in the final Congress.gov union or have an explicit evidenced exclusion.",
    floor_is_proof_of_completeness: false,
    scoring_or_promotion_allowed: false,
  },
  source_workbook: {
    path: path.resolve(inputPath),
    bytes: inputBytes.byteLength,
    sha256: sha256(inputBytes),
    sheet: sheets[0].name,
    used_range: "A1:AD45",
  },
  counts: {
    source_rows: floorRows.length,
    unique_identifiers: uniqueIdentifiers.length,
    duplicate_identifiers: duplicateIdentifiers.length,
  },
  identifier_set_sha256: sha256(`${uniqueIdentifiers.join("\n")}\n`),
  unique_identifiers: uniqueIdentifiers,
  duplicate_identifiers: duplicateIdentifiers,
  rows: floorRows,
};
await fs.writeFile(
  path.join(outputDir, "quorum_floor_manifest.json"),
  `${JSON.stringify(floorManifest, null, 2)}\n`,
  "utf8",
);

console.log(
  JSON.stringify({
    sheets: sheets.map(({ index, name, row_count, column_count }) => ({
      index,
      name,
      row_count,
      column_count,
    })),
    floor: floorManifest.counts,
    identifier_set_sha256: floorManifest.identifier_set_sha256,
  }),
);
