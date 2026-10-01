import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workspace = path.resolve(
  "C:/Users/pgoff/OneDrive/Desktop/Melange Systems",
);
const workbookPath = path.join(
  workspace,
  "Moneyball Main Version - Blended.xlsx",
);
const outputDir = path.join(
  workspace,
  "tmp",
  "legfix5_workbook_audit",
  "output",
);
await fs.mkdir(outputDir, { recursive: true });

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const inspections = {};
inspections.sheets = (
  await workbook.inspect({
    kind: "sheet",
    include: "id,name",
    maxChars: 12000,
  })
).ndjson;

for (const [name, range] of [
  ["Legislative Score - Raw", "A1:FD8"],
  ["Legislative Score - Normalized", "A1:FD8"],
  ["Blended Model", "A1:AB12"],
  ["Rank & Allocation", "A1:AB12"],
  ["Sub Layer - Raw", "A1:FD12"],
  ["Sub Layer - Normalized", "A1:FD12"],
]) {
  inspections[`${name}!${range}`] = (
    await workbook.inspect({
      kind: "table",
      sheetId: name,
      range,
      include: "values,formulas",
      tableMaxRows: 12,
      tableMaxCols: 160,
      tableMaxCellChars: 120,
      maxChars: 60000,
    })
  ).ndjson;
}

inspections.formulaErrors = (
  await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 500 },
    summary: "legislation workbook formula error scan",
    maxChars: 30000,
  })
).ndjson;

await fs.writeFile(
  path.join(outputDir, "inspection.json"),
  `${JSON.stringify(inspections, null, 2)}\n`,
  "utf8",
);

for (const [sheetName, range, filename] of [
  ["Legislative Score - Raw", "A1:FD8", "legislative_raw.png"],
  [
    "Legislative Score - Normalized",
    "A1:FD8",
    "legislative_normalized.png",
  ],
  ["Blended Model", "A1:AB12", "blended_model.png"],
  ["Rank & Allocation", "A1:AB12", "rank_allocation.png"],
  ["Sub Layer - Raw", "A1:FD12", "sub_layer_raw.png"],
  ["Sub Layer - Normalized", "A1:FD12", "sub_layer_normalized.png"],
]) {
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, filename),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

console.log(path.join(outputDir, "inspection.json"));
