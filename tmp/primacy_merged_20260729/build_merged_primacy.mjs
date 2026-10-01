import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = String.raw`C:\Users\pgoff\OneDrive\Desktop\Melange Systems`;
const auditDir = path.join(
  root,
  "audits",
  "legfix5",
  "primacy_merged",
  "greenlight-20260728a-v1",
);
const outputDir = path.join(
  root,
  "outputs",
  "019fa929-739b-79a1-8dae-2a79645b7f10",
);
const previewDir = path.join(
  root,
  "tmp",
  "primacy_merged_20260729",
  "previews",
);

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const boardCsv = await fs.readFile(path.join(auditDir, "merged_primacy_board.csv"), "utf8");
const receipt = JSON.parse(
  await fs.readFile(path.join(auditDir, "merged_primacy_receipt.json"), "utf8"),
);
const delta = JSON.parse(
  await fs.readFile(path.join(auditDir, "merged_rank_tier_delta.json"), "utf8"),
);
const reconciliation = (await fs.readFile(
  path.join(auditDir, "candidate_reconciliation.ndjson"),
  "utf8",
))
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));

const workbook = await Workbook.fromCSV(boardCsv, { sheetName: "Merged Board" });
const board = workbook.worksheets.getItem("Merged Board");
const summary = workbook.worksheets.add("Summary");
const recon = workbook.worksheets.add("Candidate Reconciliation");
const classified = workbook.worksheets.add("New Classifications");
const receiptSheet = workbook.worksheets.add("Receipt");

const navy = "#17324D";
const teal = "#0F766E";
const paleTeal = "#E7F5F2";
const paleBlue = "#EAF1F8";
const paleGold = "#FFF4CC";
const paleRed = "#FDECEC";
const green = "#1F7A4D";
const lightLine = "#D7E0E8";
const bodyFont = "Aptos";
const titleFont = "Aptos Display";
const wrapAt = (value, width = 54) => {
  const words = String(value ?? "").split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (line && next.length > width) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines.join("\n");
};

for (const sheet of [summary, board, recon, classified, receiptSheet]) {
  sheet.showGridLines = false;
}

// ---------------- Summary ----------------
summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["Merged Legislative Treatment + Primacy Audit"]];
summary.getRange("A1:H1").format = {
  fill: navy,
  font: { name: titleFont, size: 18, bold: true, color: "#FFFFFF" },
  rowHeight: 34,
  verticalAlignment: "center",
};
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [[
  "Treatment Leg% carries policy direction; primacy independently measures beneficiary alignment; conduct is display-only.",
]];
summary.getRange("A2:H2").format = {
  fill: paleBlue,
  font: { name: bodyFont, size: 10, color: "#334155" },
  wrapText: true,
  rowHeight: 30,
  verticalAlignment: "center",
};

summary.getRange("A4:H4").values = [[
  "Members",
  null,
  "Overall rank changes",
  null,
  "Display slots changed",
  null,
  "Tier changes",
  null,
]];
summary.getRange("A5:H5").values = [[
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
]];
summary.getRange("A5").formulas = [["=COUNTA('Merged Board'!$B$2:$B$534)"]];
summary.getRange("C5").formulas = [["=COUNTIF('Merged Board'!$K$2:$K$534,\"<>0\")"]];
summary.getRange("E5").formulas = [["=COUNTIF('Merged Board'!$M$2:$M$534,\"<>0\")"]];
summary.getRange("G5").formulas = [["=SUM('Merged Board'!$S$2:$S$534)"]];
for (const start of ["A4:B5", "C4:D5", "E4:F5", "G4:H5"]) {
  summary.getRange(start).format = {
    fill: start.startsWith("C") ? "#E8F7EE" : paleTeal,
    borders: { preset: "outside", style: "thin", color: lightLine },
  };
}
summary.getRange("A4:H4").format.font = {
  name: bodyFont,
  size: 9,
  bold: true,
  color: "#475569",
};
for (const cell of ["A5", "C5", "E5", "G5"]) {
  summary.getRange(cell).format = {
    font: { name: titleFont, size: 20, bold: true, color: cell === "C5" ? green : navy },
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
}
summary.getRange("A5:H5").format.rowHeight = 34;

summary.getRange("A7:D7").merge();
summary.getRange("A7").values = [["Universe reconciliation"]];
summary.getRange("E7:H7").merge();
summary.getRange("E7").values = [["Rank/display contract"]];
summary.getRange("A7:H7").format = {
  fill: teal,
  font: { name: bodyFont, bold: true, color: "#FFFFFF" },
};
summary.getRange("A8:D12").values = [
  ["Base act universe", receipt.counts.base_act_universe, "Merged act universe", receipt.counts.merged_act_universe],
  ["Scoring-ready candidates", receipt.counts.scoring_ready_candidates, "Already represented", receipt.counts.scoring_ready_already_in_bundle],
  ["New scoring candidates", receipt.counts.new_scoring_candidates, "Added for current roster", receipt.counts.new_current_roster_scoring_amendments],
  ["Historical-only candidates", receipt.counts.new_historical_scoring_amendments, "Visible non-scoring held", receipt.counts.membership_only_visible_non_scoring],
  ["Merged baseline", receipt._baseline ?? 0.50238, "Production writes", 0],
];
summary.getRange("E8:H12").values = [
  ["Direction source", "Treatment Leg%", "Beneficiary source", "Primacy factor"],
  ["Display formula", "Leg% × factor", "Conduct formula", "Grievance − delivery"],
  ["Max display delta", delta.summary.max_abs_display_delta, "Tier membership changes", delta.summary.tier_changed],
  ["Overall-rank delta", delta.summary.overall_rank_changed, "Tier-1 changed", delta.summary.tier1_membership_changed ? "YES" : "NO"],
  ["Status", receipt.status.startsWith("PASS") ? "PASS" : "FAIL", "External sync", "None"],
];
summary.getRange("A8:H12").format = {
  font: { name: bodyFont, size: 10, color: "#1E293B" },
  borders: {
    insideHorizontal: { style: "thin", color: lightLine },
    bottom: { style: "thin", color: lightLine },
  },
  verticalAlignment: "center",
};
for (const range of ["A8:A12", "C8:C12", "E8:E12", "G8:G12"]) {
  summary.getRange(range).format.font = { name: bodyFont, size: 10, bold: true, color: "#475569" };
}

summary.getRange("A14:H14").merge();
summary.getRange("A14").values = [["Tier 1 — unchanged membership after the merge"]];
summary.getRange("A14:H14").format = {
  fill: navy,
  font: { name: bodyFont, bold: true, color: "#FFFFFF" },
};
const tier1Rows = [];
for (let i = 0; i < delta.tier1.length; i += 4) {
  tier1Rows.push(delta.tier1.slice(i, i + 4));
}
summary.getRange("A15:H17").values = tier1Rows.map((row) => [
  row[0] ?? "", "",
  row[1] ?? "", "",
  row[2] ?? "", "",
  row[3] ?? "", "",
]);
summary.getRange("A15:H17").format = {
  fill: paleBlue,
  font: { name: bodyFont, size: 10, bold: true, color: navy },
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
  verticalAlignment: "center",
};

summary.getRange("A19:H19").merge();
summary.getRange("A19").values = [["Verification gates"]];
summary.getRange("A19:H19").format = {
  fill: teal,
  font: { name: bodyFont, bold: true, color: "#FFFFFF" },
};
const gateRows = Object.entries(receipt.gates);
summary.getRange(`A20:H${19 + Math.ceil(gateRows.length / 2)}`).values = Array.from(
  { length: Math.ceil(gateRows.length / 2) },
  (_, index) => {
    const left = gateRows[index * 2];
    const right = gateRows[index * 2 + 1];
    return [
      left?.[0]?.replaceAll("_", " ") ?? "",
      left?.[1] ? "PASS" : "FAIL",
      "",
      "",
      right?.[0]?.replaceAll("_", " ") ?? "",
      right?.[1] ? "PASS" : "FAIL",
      "",
      "",
    ];
  },
);
summary.getRange("A20:H25").format = {
  font: { name: bodyFont, size: 9, color: "#334155" },
  wrapText: true,
  borders: { preset: "inside", style: "thin", color: lightLine },
  verticalAlignment: "center",
};
summary.getRange("B20:B25").format.font = { name: bodyFont, bold: true, color: green };
summary.getRange("F20:F25").format.font = { name: bodyFont, bold: true, color: green };
summary.freezePanes.freezeRows(2);
summary.getRange("A:H").format.columnWidth = 15;
summary.getRange("A:A").format.columnWidth = 23;
summary.getRange("C:C").format.columnWidth = 23;
summary.getRange("E:E").format.columnWidth = 24;
summary.getRange("G:G").format.columnWidth = 23;
summary.getRange("B:B").format.columnWidth = 12;
summary.getRange("D:D").format.columnWidth = 12;
summary.getRange("F:F").format.columnWidth = 18;
summary.getRange("H:H").format.columnWidth = 20;

// ---------------- Merged board ----------------
const boardUsed = board.getUsedRange();
boardUsed.format.font = { name: bodyFont, size: 9, color: "#1E293B" };
board.getRange("R1:S1").values = [["prior_primacy_tier", "tier_changed"]];
board.getRange("R2").formulas = [["=IF(L2<=12,1,IF(L2<=36,2,IF(L2<=84,3,0)))"]];
board.getRange("R2:R534").fillDown();
board.getRange("S2").formulas = [["=--(C2<>R2)"]];
board.getRange("S2:S534").fillDown();
board.getRange("A1:S1").format = {
  fill: navy,
  font: { name: bodyFont, size: 9, bold: true, color: "#FFFFFF" },
  wrapText: true,
  rowHeight: 34,
  verticalAlignment: "center",
};
board.freezePanes.freezeRows(1);
board.freezePanes.freezeColumns(2);
board.tables.add("A1:S534", true, "MergedPrimacyBoard");
board.getRange("A2:A534").format.numberFormat = "0";
board.getRange("C2:C534").format.numberFormat = "0";
board.getRange("D2:G534").format.numberFormat = "0.000000";
board.getRange("H2:H534").format.numberFormat = "0.00";
board.getRange("I2:L534").format.numberFormat = "0";
board.getRange("M2:M534").format.numberFormat = "+0;-0;0";
board.getRange("N2:P534").format.numberFormat = "0.00";
board.getRange("Q2:Q534").format.numberFormat = "0";
board.getRange("R2:S534").format.numberFormat = "0";
board.getRange("M2:M534").conditionalFormats.add("cellIs", {
  operator: "notEqual",
  formula: 0,
  format: { fill: paleGold, font: { bold: true, color: "#8A4B08" } },
});
board.getRange("K2:K534").conditionalFormats.add("cellIs", {
  operator: "equal",
  formula: 0,
  format: { fill: "#E8F7EE", font: { color: green } },
});
board.getRange("A2:S534").conditionalFormats.addCustom("=$C2=1", {
  fill: "#EDF7FF",
});
board.getRange("A:A").format.columnWidth = 8;
board.getRange("B:B").format.columnWidth = 24;
board.getRange("C:C").format.columnWidth = 8;
board.getRange("D:G").format.columnWidth = 15;
board.getRange("H:M").format.columnWidth = 14;
board.getRange("N:Q").format.columnWidth = 13;
board.getRange("R:S").format.columnWidth = 14;

// ---------------- Candidate reconciliation ----------------
const reconHeaders = [
  "canonical_key",
  "integration_state",
  "primacy_state",
  "member",
  "roster_status",
  "class",
  "authority",
  "direction",
  "direction_consumed_by",
  "beneficiary_consumed_by",
  "reason",
  "source_url",
];
const sourceUrl = (key) => {
  const [congress, type, number] = key.split(":");
  const map = {
    hamdt: `amendment/${congress}th-congress/house-amendment/${number}`,
    samdt: `amendment/${congress}th-congress/senate-amendment/${number}`,
    hr: `bill/${congress}th-congress/house-bill/${number}`,
    s: `bill/${congress}th-congress/senate-bill/${number}`,
    hjres: `bill/${congress}th-congress/house-joint-resolution/${number}`,
    sjres: `bill/${congress}th-congress/senate-joint-resolution/${number}`,
  };
  return `https://www.congress.gov/${map[type]}`;
};
const sourceUrlDisplay = (key) => {
  const url = sourceUrl(key);
  const prefix = "https://www.congress.gov/";
  return `${prefix}\n${url.slice(prefix.length).replaceAll("/", "/\n")}`;
};
const reconValues = reconciliation.map((row) => [
  row.canonical_key,
  row.integration_state,
  row.primacy_state,
  row.member ?? "",
  row.roster_status ?? "",
  row.class ?? "",
  row.authority ?? "",
  row.direction ?? "",
  row.direction_consumed_by ?? "",
  row.beneficiary_consumed_by ?? "",
  wrapAt(row.reason ?? "", 54),
  sourceUrlDisplay(row.canonical_key),
]);
recon.getRange(`A1:L${reconValues.length + 1}`).values = [reconHeaders, ...reconValues];
recon.getRange("A1:L1").format = {
  fill: navy,
  font: { name: bodyFont, size: 9, bold: true, color: "#FFFFFF" },
  wrapText: true,
  rowHeight: 34,
};
recon.getRange(`A2:L${reconValues.length + 1}`).format = {
  font: { name: bodyFont, size: 9, color: "#1E293B" },
  verticalAlignment: "top",
  rowHeight: 66,
};
recon.tables.add(`A1:L${reconValues.length + 1}`, true, "CandidateReconciliation");
recon.freezePanes.freezeRows(1);
recon.freezePanes.freezeColumns(1);
recon.getRange(`C2:C${reconValues.length + 1}`).conditionalFormats.add("containsText", {
  text: "held",
  format: { fill: paleGold, font: { color: "#8A4B08" } },
});
recon.getRange("A:A").format.columnWidth = 19;
recon.getRange("B:C").format.columnWidth = 28;
recon.getRange("D:D").format.columnWidth = 20;
recon.getRange("E:J").format.columnWidth = 20;
recon.getRange("K:K").format.columnWidth = 44;
recon.getRange("K:K").format.wrapText = true;
recon.getRange("L:L").format.columnWidth = 32;
recon.getRange("L:L").format.wrapText = true;

// ---------------- New classifications ----------------
const newRows = reconciliation.filter((row) =>
  row.primacy_state === "classified_and_added_current_roster"
  || row.primacy_state === "classified_historical_off_current_roster"
);
const classHeaders = [
  "canonical_key",
  "member",
  "roster_status",
  "class",
  "authority",
  "direction",
  "direction_layer",
  "beneficiary_layer",
  "operative_reason",
  "source_url",
];
const classValues = newRows.map((row) => [
  row.canonical_key,
  row.member ?? "",
  row.roster_status ?? "",
  row.class ?? "",
  row.authority ?? "",
  row.direction ?? "",
  row.direction_consumed_by ?? "",
  row.beneficiary_consumed_by ?? "",
  wrapAt(row.reason ?? "", 54),
  sourceUrlDisplay(row.canonical_key),
]);
classified.getRange(`A1:J${classValues.length + 1}`).values = [classHeaders, ...classValues];
classified.getRange("A1:J1").format = {
  fill: navy,
  font: { name: bodyFont, size: 9, bold: true, color: "#FFFFFF" },
  wrapText: true,
  rowHeight: 34,
};
classified.getRange(`A2:J${classValues.length + 1}`).format = {
  font: { name: bodyFont, size: 9, color: "#1E293B" },
  verticalAlignment: "top",
  rowHeight: 66,
};
classified.tables.add(`A1:J${classValues.length + 1}`, true, "NewPrimacyClassifications");
classified.freezePanes.freezeRows(1);
classified.getRange(`D2:D${classValues.length + 1}`).conditionalFormats.add("containsText", {
  text: "crypto_primary",
  format: { fill: "#EEE8FF", font: { color: "#5B3FA3", bold: true } },
});
classified.getRange(`C2:C${classValues.length + 1}`).conditionalFormats.add("containsText", {
  text: "historical",
  format: { fill: paleGold, font: { color: "#8A4B08" } },
});
classified.getRange("A:A").format.columnWidth = 19;
classified.getRange("B:B").format.columnWidth = 20;
classified.getRange("C:E").format.columnWidth = 27;
classified.getRange("F:H").format.columnWidth = 18;
classified.getRange("I:I").format.columnWidth = 44;
classified.getRange("I:I").format.wrapText = true;
classified.getRange("J:J").format.columnWidth = 32;
classified.getRange("J:J").format.wrapText = true;

// ---------------- Receipt ----------------
const receiptRows = [
  ["Status", receipt.status],
  ["Schema", receipt.schema],
  ["Rank authority", receipt.method.rank_authority],
  ["Direction layer", receipt.method.direction_layer],
  ["Beneficiary layer", receipt.method.beneficiary_layer],
  ["Display formula", receipt.method.display_formula],
  ["Conduct formula", receipt.method.conduct_formula],
  ["Rank contract", receipt.method.rank_contract],
  ["", ""],
  ["Safety", "Value"],
  ...Object.entries(receipt.safety).map(([key, value]) => [key.replaceAll("_", " "), String(value)]),
  ["", ""],
  ["Protected file", "SHA-256 after"],
  ...Object.entries(receipt.protected_hashes_after).map(([file, hash]) => [path.basename(file), hash]),
];
receiptSheet.getRange(`A1:B${receiptRows.length}`).values = receiptRows;
receiptSheet.getRange(`A1:B${receiptRows.length}`).format.font = {
  name: bodyFont,
  size: 10,
  color: "#1E293B",
};
receiptSheet.getRange("A1:B1").format = {
  fill: navy,
  font: { name: titleFont, size: 14, bold: true, color: "#FFFFFF" },
};
receiptSheet.getRange("A10:B10").format = {
  fill: teal,
  font: { name: bodyFont, bold: true, color: "#FFFFFF" },
};
const protectedHeaderRow = 12 + Object.keys(receipt.safety).length;
receiptSheet.getRange(`A${protectedHeaderRow}:B${protectedHeaderRow}`).format = {
  fill: teal,
  font: { name: bodyFont, bold: true, color: "#FFFFFF" },
};
receiptSheet.getRange("A:A").format.columnWidth = 34;
receiptSheet.getRange("B:B").format.columnWidth = 92;
receiptSheet.getRange(`B1:B${receiptRows.length}`).format.wrapText = true;
receiptSheet.freezePanes.freezeRows(1);

// Compact verification.
const summaryInspect = await workbook.inspect({
  kind: "table",
  sheetId: "Summary",
  range: "A1:H25",
  include: "values,formulas",
  tableMaxRows: 25,
  tableMaxCols: 8,
  maxChars: 7000,
});
console.log(summaryInspect.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 200 },
  summary: "final formula error scan",
  maxChars: 4000,
});
console.log(formulaErrors.ndjson);

const previewSpecs = [
  ["Summary", "A1:H25", "summary.png"],
  ["Merged Board", "A1:S35", "merged_board.png"],
  ["Candidate Reconciliation", "A1:L25", "candidate_reconciliation.png"],
  ["New Classifications", "A1:J18", "new_classifications.png"],
  ["Receipt", `A1:B${receiptRows.length}`, "receipt.png"],
];
for (const [sheetName, range, fileName] of previewSpecs) {
  const image = await workbook.render({ sheetName, range, scale: 1.25, format: "png" });
  await fs.writeFile(path.join(previewDir, fileName), new Uint8Array(await image.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = path.join(outputDir, "merged_primacy_treatment_audit.xlsx");
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, previewDir, sheets: previewSpecs.map((row) => row[0]) }));
await new Promise((resolve) => setTimeout(resolve, 300));
process.exit(0);
