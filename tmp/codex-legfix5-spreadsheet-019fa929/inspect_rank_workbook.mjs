import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath =
  "C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legfix5/production_baseline_full_downstream/files/Moneyball Main Version - Blended.xlsx";

const blob = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(blob);

const sheetSummary = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 12000,
});
console.log("SHEETS");
console.log(sheetSummary.ndjson);

for (const [sheetId, range] of [
  ["Blended Model", "A1:AB8"],
  ["Rank & Allocation", "A1:AB8"],
  ["Success - Sponsor", "A1:V8"],
  ["Press Release - Normalized", "A1:T5"],
]) {
  const inspection = await workbook.inspect({
    kind: "region",
    sheetId,
    range,
    include: "values,formulas",
    maxChars: 16000,
  });
  console.log(`REGION ${sheetId}!${range}`);
  console.log(inspection.ndjson);
}

const blended = workbook.worksheets.getItem("Blended Model");
for (const address of ["O3", "S3", "T3", "AB2", "AB3", "AB4", "AB5"]) {
  const range = blended.getRange(address);
  console.log(
    JSON.stringify({
      cell: `Blended Model!${address}`,
      values: range.values,
      formulas: range.formulas,
      displayFormulas: range.displayFormulas,
    }),
  );
}
