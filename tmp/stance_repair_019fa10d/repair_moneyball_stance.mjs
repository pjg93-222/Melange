import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workspace = process.argv[2];
const outputDir = process.argv[3];
if (!workspace || !outputDir) throw new Error("usage: node repair_moneyball_stance.mjs WORKSPACE OUTPUT_DIR");

const inputPath = path.join(workspace, "Moneyball Main Version - Blended.xlsx");
const outputPath = path.join(outputDir, "Moneyball Main Version - Blended.repaired.xlsx");
const previewDir = path.join(outputDir, "previews");
const category = JSON.parse(await fs.readFile(path.join(workspace, "category_stance.json"), "utf8"));
await fs.mkdir(previewDir, { recursive: true });

const generalTiers = [
  "Champion", "Ally", "Highly Persuadable", "Persuadable", "Lean Persuadable",
  "True Neutral", "Lean Skeptic", "Skeptic", "Highly Skeptical", "Opponent", "—",
];
const categoryTiers = ["Champion", "Defender", ...generalTiers.slice(1)];
const colors = {
  Champion: "#63BE7B", Defender: "#2DD4BF", Ally: "#C6EFCE",
  "Highly Persuadable": "#BDD7EE", Persuadable: "#D9EAF7",
  "Lean Persuadable": "#FFF2CC", "True Neutral": "#E7E7E7",
  "Lean Skeptic": "#FCE4D6", Skeptic: "#FFC7CE",
  "Highly Skeptical": "#F4B084", Opponent: "#F8696B", "—": "#F2F2F2",
};
const headerFormat = {
  fill: "#253A5A",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#D9E2F3" },
};
const bodyFormat = {
  font: { size: 9, color: "#1F2937" },
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: "#E5E7EB" },
};

async function saveRender(workbook, sheetName, filename, range = "A1:Z30", scale = 0.65) {
  const blob = await workbook.render({ sheetName, range, scale, format: "png" });
  await fs.writeFile(path.join(previewDir, filename), new Uint8Array(await blob.arrayBuffer()));
}

console.log("IMPORT_START", new Date().toISOString());
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
console.log("IMPORT_DONE", new Date().toISOString());

const summary = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 12000,
});
console.log("SHEET_SUMMARY", summary.ndjson || summary);

await saveRender(workbook, "Category Stance", "before-category-stance.png", "A1:T24", 0.8);
await saveRender(workbook, "Coalition Profiles", "before-coalition-profiles.png", "A1:P24", 0.9);
console.log("BEFORE_RENDER_DONE", new Date().toISOString());

const ra = workbook.worksheets.getItem("Rank & Allocation");
const cs = workbook.worksheets.getItem("Category Stance");
const cp = workbook.worksheets.getItem("Coalition Profiles");
const roster = ra.getRange("A3:A535").values.flat();
const overallValues = ra.getRange("G3:G535").values.flat();
if (roster.length !== 533 || roster.some((name) => !name)) throw new Error("Rank & Allocation roster is not 533 complete rows");
const overall = Object.fromEntries(roster.map((name, index) => [name, overallValues[index] || "—"]));
const champions = roster.filter((name) => overall[name] === "Champion");
if (champions.length !== 12) throw new Error(`Expected exactly 12 current Champions, found ${champions.length}`);
if (JSON.stringify(new Set(roster).size) !== JSON.stringify(533)) throw new Error("Rank & Allocation roster contains duplicates");
if (new Set(roster).size !== Object.keys(category.matrix).length || roster.some((name) => !category.matrix[name])) {
  throw new Error("category_stance.json roster does not exactly match Rank & Allocation");
}

cs.getRange("A1:T538").clear({ applyTo: "all" });
cs.getRange("A1:T1").values = [["Member", "General Stance", ...category.cats]];
cs.getRange("A1:T1").format = { ...headerFormat, rowHeight: 46 };
const categoryRows = roster.map((name) => [
  name,
  overall[name],
  ...category.cats.map((cat) => category.matrix[name][cat] || "—"),
]);
cs.getRange("A2:T534").values = categoryRows;
cs.getRange("A2:T534").format = { ...bodyFormat, horizontalAlignment: "center" };
cs.getRange("A2:A534").format = { ...bodyFormat, horizontalAlignment: "left" };
const categoryBody = cs.getRange("B2:T534");
categoryBody.conditionalFormats.deleteAll();
for (const tier of categoryTiers) {
  categoryBody.conditionalFormats.addCustom(`=B2="${tier}"`, {
    fill: colors[tier],
    font: { bold: tier === "Champion" || tier === "Opponent" },
  });
}
cs.getRange("A536:T536").merge();
cs.getRange("A536:T536").values = [["Legend — stance toward the CU position, by category"]];
cs.getRange("A536:T536").format = {
  fill: "#D9E2F3", font: { bold: true, color: "#253A5A" },
  horizontalAlignment: "left", verticalAlignment: "center",
};
cs.getRange("A537:L537").values = [categoryTiers];
for (let index = 0; index < categoryTiers.length; index += 1) {
  const cell = cs.getCell(536, index);
  cell.format = {
    fill: colors[categoryTiers[index]],
    font: { bold: categoryTiers[index] === "Champion" || categoryTiers[index] === "Opponent" },
    horizontalAlignment: "center", verticalAlignment: "center",
  };
}
cs.getRange("A538:T538").merge();
cs.getRange("A538:T538").values = [[
  "Source: category_stance.json. General Stance matches Rank & Allocation column G. Overall Champion is reserved for Legislative+Press Tier 1 (top 12).",
]];
cs.getRange("A538:T538").format = { font: { italic: true, color: "#4B5563" }, wrapText: true };
cs.getRange("A:A").format.columnWidth = 24;
cs.getRange("B:B").format.columnWidth = 19;
cs.getRange("C:T").format.columnWidth = 17;
cs.freezePanes.unfreeze();
cs.freezePanes.freezeRows(1);
cs.freezePanes.freezeColumns(2);
cs.showGridLines = false;

cp.getRange("J3:U13").clear({ applyTo: "all" });
cp.getRange("J3:T3").values = [generalTiers];
for (let index = 0; index < generalTiers.length; index += 1) {
  cp.getCell(2, 9 + index).format = {
    fill: colors[generalTiers[index]], font: { bold: true, color: "#1F2937" },
    horizontalAlignment: "center", verticalAlignment: "center", wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D1D5DB" },
  };
}
cp.getRange("U3").values = [["Dominant Stance"]];
cp.getRange("U3").format = headerFormat;
const blocFormulas = [];
const dominantFormulas = [];
for (let row = 4; row <= 12; row += 1) {
  blocFormulas.push(generalTiers.map((_, offset) => {
    const col = String.fromCharCode("J".charCodeAt(0) + offset);
    return `=COUNTIFS('Rank & Allocation'!$H$3:$H$535,$A${row},'Rank & Allocation'!$G$3:$G$535,${col}$3)`;
  }));
  dominantFormulas.push([`=INDEX($J$3:$T$3,MATCH(MAX(J${row}:T${row}),J${row}:T${row},0))`]);
}
cp.getRange("J4:T12").formulas = blocFormulas;
cp.getRange("U4:U12").formulas = dominantFormulas;
cp.getRange("J4:U12").format = { ...bodyFormat, horizontalAlignment: "center" };
cp.getRange("J13:T13").formulas = [[
  "=SUM(J4:J12)", "=SUM(K4:K12)", "=SUM(L4:L12)", "=SUM(M4:M12)",
  "=SUM(N4:N12)", "=SUM(O4:O12)", "=SUM(P4:P12)", "=SUM(Q4:Q12)",
  "=SUM(R4:R12)", "=SUM(S4:S12)", "=SUM(T4:T12)",
]];
cp.getRange("J13:T13").format = { fill: "#D9E2F3", font: { bold: true }, horizontalAlignment: "center" };
cp.getRange("J:T").format.columnWidth = 17;
cp.getRange("U:U").format.columnWidth = 20;

cp.getRange("A17:F29").clear({ applyTo: "all" });
cp.getRange("A17:F17").values = [["Stance", "Members", "Mean Score", "Allocation", "% of Pot", "Funded"]];
cp.getRange("A17:F17").format = headerFormat;
const summaryValues = generalTiers.map((tier) => [tier, null, null, null, null, null]);
cp.getRange("A18:F28").values = summaryValues;
for (let index = 0; index < generalTiers.length; index += 1) {
  cp.getCell(17 + index, 0).format = {
    fill: colors[generalTiers[index]], font: { bold: true }, verticalAlignment: "center",
  };
}
const summaryFormulas = [];
for (let row = 18; row <= 28; row += 1) {
  summaryFormulas.push([
    `=COUNTIF('Rank & Allocation'!$G$3:$G$535,$A${row})`,
    `=IFERROR(AVERAGEIF('Rank & Allocation'!$G$3:$G$535,$A${row},'Blended Model'!$S$3:$S$535),0)`,
    `=SUMIFS('Blended Model'!$U$3:$U$535,'Rank & Allocation'!$G$3:$G$535,$A${row})`,
    `=IFERROR(D${row}/'Blended Model'!$AB$6,0)`,
    `=COUNTIFS('Rank & Allocation'!$G$3:$G$535,$A${row},'Blended Model'!$U$3:$U$535,">0")`,
  ]);
}
cp.getRange("B18:F28").formulas = summaryFormulas;
cp.getRange("A18:F28").format = bodyFormat;
cp.getRange("B18:B28").format.numberFormat = "0";
cp.getRange("C18:C28").format.numberFormat = "0.000";
cp.getRange("D18:D28").format.numberFormat = "$#,##0";
cp.getRange("E18:E28").format.numberFormat = "0.0%";
cp.getRange("F18:F28").format.numberFormat = "0";
cp.getRange("A29:F29").values = [["TOTAL", null, null, null, null, null]];
cp.getRange("B29:F29").formulas = [[
  "=SUM(B18:B28)", "=AVERAGE('Blended Model'!$S$3:$S$535)",
  "=SUM(D18:D28)", "=SUM(E18:E28)", "=SUM(F18:F28)",
]];
cp.getRange("A29:F29").format = headerFormat;
cp.getRange("B29").format.numberFormat = "0";
cp.getRange("C29").format.numberFormat = "0.000";
cp.getRange("D29").format.numberFormat = "$#,##0";
cp.getRange("E29").format.numberFormat = "0.0%";
cp.getRange("F29").format.numberFormat = "0";
cp.showGridLines = false;

console.log("EDIT_DONE", new Date().toISOString(), "CHAMPIONS", champions.join(" | "));
console.log("CATEGORY_CHECK", (await workbook.inspect({ kind: "region", sheetId: "Category Stance", range: "A1:T8", maxChars: 6000 })).ndjson);
console.log("COALITION_FORMULA_CHECK", (await workbook.inspect({ kind: "formula", sheetId: "Coalition Profiles", range: "J3:U29", maxChars: 8000, options: { maxResults: 180 } })).ndjson);

await saveRender(workbook, "Category Stance", "after-category-stance.png", "A1:T24", 0.8);
await saveRender(workbook, "Coalition Profiles", "after-coalition-profiles.png", "A1:U29", 0.8);
console.log("TARGET_RENDER_DONE", new Date().toISOString());

const sheetItems = workbook.worksheets.items || [];
for (let index = 0; index < sheetItems.length; index += 1) {
  const name = sheetItems[index].name;
  const safe = String(index + 1).padStart(2, "0") + "-" + name.replace(/[<>:\"/\\|?*]+/g, "_");
  try {
    await saveRender(workbook, name, `sheet-${safe}.png`, "A1:Z30", 0.45);
    console.log("RENDER_OK", name);
  } catch (error) {
    console.log("RENDER_WARN", name, String(error));
  }
}

console.log("EXPORT_START", new Date().toISOString());
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log("EXPORT_DONE", outputPath, new Date().toISOString());
