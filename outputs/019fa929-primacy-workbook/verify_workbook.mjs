import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const mode = process.argv[2] || "pre";
const root = "C:\\Users\\pgoff\\OneDrive\\Desktop\\Melange Systems";
const outputDir = path.join(root, "outputs", "019fa929-primacy-workbook");
const sourcePath = path.join(root, "Moneyball Main Version - Blended.xlsx");

await fs.mkdir(outputDir, { recursive: true });
const input = await FileBlob.load(sourcePath);
const workbook = await SpreadsheetFile.importXlsx(input);

const sheetSummary = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 12000,
});
console.log("SHEETS");
console.log(sheetSummary.ndjson);

if (mode === "pre") {
  const preview = await workbook.render({
    sheetName: "Rank & Allocation",
    range: "A1:N28",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, "pre_rank_allocation.png"),
    new Uint8Array(await preview.arrayBuffer()),
  );
  console.log("PREVIEW_SAVED");
  process.exit(0);
}

const rankCheck = await workbook.inspect({
  kind: "table",
  range: "Rank & Allocation!A1:N28",
  include: "values,formulas",
  tableMaxRows: 28,
  tableMaxCols: 14,
  maxChars: 16000,
});
console.log("RANK_CHECK");
console.log(rankCheck.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
  maxChars: 12000,
});
console.log("FORMULA_ERRORS");
console.log(formulaErrors.ndjson);

const rendered = [];
for (const sheet of workbook.worksheets.items) {
  const safeName = sheet.name.replace(/[<>:"/\\|?*]+/g, "_");
  const preview = await workbook.render({
    sheetName: sheet.name,
    range: "A1:N30",
    scale: 1,
    format: "png",
  });
  const previewPath = path.join(outputDir, `post_${safeName}.png`);
  await fs.writeFile(
    previewPath,
    new Uint8Array(await preview.arrayBuffer()),
  );
  rendered.push({ sheet: sheet.name, previewPath });
}
console.log("RENDERED");
console.log(JSON.stringify(rendered));

const outputPath = path.join(outputDir, "Moneyball Main Version - Blended.xlsx");
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log("OUTPUT");
console.log(outputPath);
