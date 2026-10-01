import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath =
  "C:\\Users\\pgoff\\OneDrive\\Desktop\\Melange Systems\\audits\\legfix5\\production_baseline_full_downstream\\files\\Moneyball Main Version - Blended.xlsx";
const outputDir =
  "C:\\Users\\pgoff\\OneDrive\\Desktop\\Melange Systems\\tmp\\cfpb_shadow_artifact";

await fs.mkdir(outputDir, { recursive: true });
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));

const sheets = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 10000,
});

const targets = [
  ["Legislative Score - Raw", "CU1:EV8"],
  ["Legislative Score - Normalized", "CU1:EV5"],
  ["Rank & Allocation", "A1:E6"],
  ["Blended Model", "A1:T6"],
];

const results = { sheets: sheets.ndjson, targets: [] };
for (const [sheetId, range] of targets) {
  const inspected = await workbook.inspect({
    kind: "table",
    sheetId,
    range,
    include: "values,formulas",
    tableMaxRows: 12,
    tableMaxCols: 80,
    maxChars: 60000,
  });
  results.targets.push({ sheetId, range, ndjson: inspected.ndjson });
}

const rawSheet = workbook.worksheets.getItem("Legislative Score - Raw");
const normSheet = workbook.worksheets.getItem("Legislative Score - Normalized");
const rankSheet = workbook.worksheets.getItem("Rank & Allocation");
const blendedSheet = workbook.worksheets.getItem("Blended Model");
results.direct = {
  rawHeaders: rawSheet.getRange("CU1:EV2").values,
  rawValues: rawSheet.getRange("CU3:EV535").values,
  normHeaders: normSheet.getRange("CU1:EV2").values,
  normValues: normSheet.getRange("CU3:EV535").values,
  normFormulas: normSheet.getRange("CU3:EV6").formulas,
  rankValues: rankSheet.getRange("A1:E6").values,
  rankFormulas: rankSheet.getRange("A1:E6").formulas,
  blendedValues: blendedSheet.getRange("A1:T6").values,
  blendedFormulas: blendedSheet.getRange("A1:T6").formulas,
};

function columnStats(values, startColNumber, selectedColumns) {
  const lettersToNumber = (letters) =>
    [...letters].reduce((acc, ch) => acc * 26 + ch.charCodeAt(0) - 64, 0);
  const stats = {};
  for (const col of selectedColumns) {
    const idx = lettersToNumber(col) - startColNumber;
    let nonzero = 0;
    let sum = 0;
    let min = null;
    let max = null;
    for (const row of values) {
      const value = row[idx];
      if (typeof value === "number" && Number.isFinite(value)) {
        if (value !== 0) nonzero += 1;
        sum += value;
        min = min === null ? value : Math.min(min, value);
        max = max === null ? value : Math.max(max, value);
      }
    }
    stats[col] = { nonzero, sum, min, max };
  }
  return stats;
}

results.rawStats = columnStats(results.direct.rawValues, 99, [
  "CU",
  "CV",
  "CW",
  "CX",
  "CY",
  "CZ",
  "DA",
  "DB",
  "EO",
  "EP",
  "EQ",
  "ER",
  "ES",
  "ET",
  "EU",
  "EV",
]);
results.normStats = columnStats(results.direct.normValues, 99, [
  "CU",
  "CV",
  "CW",
  "CX",
  "CY",
  "EO",
  "EP",
  "EQ",
  "ER",
  "ES",
]);

await fs.writeFile(
  path.join(outputDir, "inspection.json"),
  JSON.stringify(results, null, 2),
);

for (const [sheetName, range, fileName] of [
  ["Legislative Score - Raw", "CU1:EV8", "raw-cfpb.png"],
  ["Rank & Allocation", "A1:E12", "rank-preview.png"],
  ["Blended Model", "A1:T12", "blended-preview.png"],
]) {
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 1.5,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, fileName),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

console.log(
  JSON.stringify(
    {
      rawStats: results.rawStats,
      normStats: results.normStats,
      rankD3Formula: results.direct.rankFormulas[2][3],
      blendedD3Formula: results.direct.blendedFormulas[2][3],
      previews: ["raw-cfpb.png", "rank-preview.png", "blended-preview.png"],
    },
    null,
    2,
  ),
);
