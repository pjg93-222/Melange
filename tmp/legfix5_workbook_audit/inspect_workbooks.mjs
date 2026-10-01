import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [workbookPath] = process.argv.slice(2);
if (!workbookPath) {
  throw new Error("Usage: inspect_workbooks.mjs <workbook.xlsx>");
}

async function load(path) {
  const input = await FileBlob.load(path);
  return SpreadsheetFile.importXlsx(input);
}

const workbook = await load(workbookPath);
const inspection = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 20000,
});

process.stdout.write(JSON.stringify({
  workbook: workbookPath,
  sheets: inspection.ndjson,
}, null, 2));
