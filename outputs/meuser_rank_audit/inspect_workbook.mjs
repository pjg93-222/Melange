import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const path = process.argv[2];
if (!path) throw new Error("usage: inspect_workbook.mjs <xlsx>");

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
const sheets = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 6000,
});
console.log("SHEETS");
console.log(sheets.ndjson);

for (const term of ["Daniel Meuser", "Press Release - Raw", "Legislative", "Overall Rank"]) {
  const matches = await workbook.inspect({
    kind: "match",
    searchTerm: term,
    options: { maxResults: 30 },
    maxChars: 10000,
    summary: `matches for ${term}`,
  });
  console.log(`MATCH ${term}`);
  console.log(matches.ndjson);
}
