import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const here = path.dirname(fileURLToPath(import.meta.url));
const manifestPath = path.join(here, "validation_manifest_150.json");
const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
const items = manifest.items;
if (items.length !== 150) throw new Error(`Expected 150 cases, got ${items.length}`);

const threadId = "019fa014-1de3-7111-a692-280ee4652bbd";
const outputDir = path.join(here, "outputs", threadId);
const previewDir = path.join(outputDir, "previews");
await fs.mkdir(previewDir, { recursive: true });

const workbook = Workbook.create();
const readme = workbook.worksheets.add("README");
const register = workbook.worksheets.add("Case Register");
const coderA = workbook.worksheets.add("Coder A Cases");
const eventsA = workbook.worksheets.add("Coder A Events");
const coderB = workbook.worksheets.add("Coder B Cases");
const eventsB = workbook.worksheets.add("Coder B Events");
const identity = workbook.worksheets.add("Identity Key");
const adjudication = workbook.worksheets.add("Adjudication");
const lists = workbook.worksheets.add("Lists");

const navy = "#17324D";
const blue = "#2C638D";
const teal = "#1F7A74";
const paleBlue = "#EAF2F8";
const paleTeal = "#E8F4F2";
const paleGold = "#FFF3CD";
const paleRed = "#FCE8E6";
const grid = "#D6DEE5";
const white = "#FFFFFF";
const ink = "#1F2933";

function titleBand(sheet, title, subtitle, endColumn) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${endColumn}1`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${endColumn}1`).format = {
    fill: navy,
    font: { bold: true, color: white, size: 16 },
    rowHeight: 28,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${endColumn}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endColumn}2`).format = {
    fill: paleBlue,
    font: { color: ink, italic: true, size: 10 },
    wrapText: true,
    rowHeight: 34,
    verticalAlignment: "center",
  };
}

function styleHeader(sheet, address) {
  sheet.getRange(address).format = {
    fill: blue,
    font: { bold: true, color: white },
    wrapText: true,
    verticalAlignment: "center",
    horizontalAlignment: "center",
    rowHeight: 34,
    borders: { preset: "all", style: "thin", color: grid },
  };
}

function styleBody(sheet, address) {
  sheet.getRange(address).format = {
    font: { color: ink, size: 10 },
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: grid },
  };
}

function absoluteMedia(item) {
  return path.join(here, "media", `${item.case_id}.mp4`);
}

function absoluteStoryboard(item) {
  return path.join(here, "storyboards", `${item.case_id}.jpg`);
}

// README
titleBand(
  readme,
  "Interview A/V Human Validation — 150 Cases",
  "Machine-prepared, blinded two-coder packet. Complete human coding before any Gemini comparison or personality/behavioral production use.",
  "H",
);
readme.getRange("A4:H4").merge();
readme.getRange("A4").values = [["STOP: Coder A and Coder B must not open Identity Key or Adjudication until both independent passes are complete."]];
readme.getRange("A4:H4").format = {
  fill: paleRed,
  font: { bold: true, color: "#8B1E1E" },
  wrapText: true,
  rowHeight: 34,
  verticalAlignment: "center",
};
const readmeRows = [
  ["Phase", "Owner", "Action", "Output / gate", "", "", "", ""],
  ["1", "Coder A", "Review all 150 clips; complete Coder A Cases and time-local Coder A Events.", "Do not use outside identity information.", "", "", "", ""],
  ["2", "Coder B", "Independently repeat the review in the B sheets.", "Do not inspect Coder A entries.", "", "", "", ""],
  ["3", "Adjudicator", "Open Identity Key and Adjudication; resolve every REVIEW row and record a rationale.", "Exclude unresolved or technically incomplete cases.", "", "", "", ""],
  ["4", "Machine validation", "Return this workbook without renaming sheets or case IDs.", "Only then compare Gemini Flash against the adjudicated human reference.", "", "", "", ""],
];
readme.getRange("A6:H10").values = readmeRows;
styleHeader(readme, "A6:H6");
styleBody(readme, "A7:H10");
readme.getRange("A12:B18").values = [
  ["Frozen sample", "150 programs"],
  ["Core / challenge", "120 / 30"],
  ["House / Senate", "134 / 16"],
  ["Distinct members", String(manifest.selected_summary.distinct_members)],
  ["Years", "2020–2025"],
  ["Production consumers", "0 (must remain zero)"],
  ["Full instructions", "HUMAN_ANNOTATION_CODEBOOK.md"],
];
readme.getRange("A12:A18").format = { fill: paleTeal, font: { bold: true, color: ink } };
styleBody(readme, "A12:B18");
readme.getRange("D12:H18").merge(true);
readme.getRange("D12").values = [["Scope boundary"]];
readme.getRange("D13").values = [[
  "Code observable speaker identity evidence, turn ownership, A/V relation, and time-local audio/visual events. Do not infer Big Five, personality, diagnosis, honesty, motive, intent, or other latent traits. The eligible source corpus is chamber-imbalanced; all 16 available Senate programs are included, so chamber comparisons are not balanced."
]];
readme.getRange("D12:H12").format = { fill: paleGold, font: { bold: true, color: ink } };
readme.getRange("D13:H18").format = { wrapText: true, verticalAlignment: "top", fill: "#FFFDF5", font: { color: ink } };
readme.getRange("A:H").format.columnWidth = 16;
readme.getRange("B:B").format.columnWidth = 22;
readme.getRange("C:C").format.columnWidth = 56;
readme.getRange("D:H").format.columnWidth = 20;
readme.freezePanes.freezeRows(4);

// Blinded register
titleBand(
  register,
  "Blinded Case Register",
  "Technical locations and target intervals only. Expected identities and source titles are sealed on Identity Key.",
  "J",
);
const registerHeaders = [
  "case_id", "media_file", "storyboard_file", "clip_duration_sec",
  "target_start_sec", "target_end_sec", "year", "chamber",
  "sample_tier", "automated_risk_flags",
];
register.getRange("A4:J4").values = [registerHeaders];
const registerRows = items.map((item) => [
  item.case_id,
  absoluteMedia(item),
  absoluteStoryboard(item),
  item.duration_sec,
  item.target_start_sec_in_clip,
  item.target_end_sec_in_clip,
  item.year,
  item.current_chamber,
  item.label_risk_tier,
  item.label_risk_flags.join("; "),
]);
register.getRange(`A5:J${items.length + 4}`).values = registerRows;
styleHeader(register, "A4:J4");
styleBody(register, `A5:J${items.length + 4}`);
register.getRange(`D5:F${items.length + 4}`).format.numberFormat = "0.0";
register.tables.add(`A4:J${items.length + 4}`, true, "CaseRegisterTable");
register.freezePanes.freezeRows(4);
register.freezePanes.freezeColumns(1);
register.getRange("A:A").format.columnWidth = 11;
register.getRange("B:C").format.columnWidth = 48;
register.getRange("D:F").format.columnWidth = 15;
register.getRange("G:I").format.columnWidth = 13;
register.getRange("J:J").format.columnWidth = 28;

const caseHeaders = [
  "case_id", "media_file", "storyboard_file", "target_start_sec",
  "target_end_sec", "media_playable", "audio_present", "video_present",
  "lower_third_text", "introduced_name", "primary_visible_person",
  "primary_audible_speaker", "target_turn_owner",
  "on_clip_identity_name", "identity_evidence",
  "identity_evidence_consistent", "speaker_count", "offscreen_speech",
  "av_relation", "ownership_confidence", "coder_notes", "coder_complete",
];
function buildCoderSheet(sheet, tableName, coderName) {
  titleBand(
    sheet,
    `${coderName} — Case Coding`,
    "Work independently. Use only the supplied clip and storyboard; record literal observations. See the codebook for category definitions.",
    "V",
  );
  sheet.getRange("A4:V4").values = [caseHeaders];
  const rows = items.map((item) => [
    item.case_id,
    absoluteMedia(item),
    absoluteStoryboard(item),
    item.target_start_sec_in_clip,
    item.target_end_sec_in_clip,
    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
  ]);
  sheet.getRange(`A5:V${items.length + 4}`).values = rows;
  styleHeader(sheet, "A4:V4");
  styleBody(sheet, `A5:V${items.length + 4}`);
  sheet.getRange(`D5:E${items.length + 4}`).format.numberFormat = "0.0";
  sheet.getRange(`Q5:Q${items.length + 4}`).format.numberFormat = "0";
  sheet.getRange(`T5:T${items.length + 4}`).format.numberFormat = "0";
  const yesNo = { rule: { type: "list", values: ["yes", "no"] } };
  sheet.getRange(`F5:H${items.length + 4}`).dataValidation = yesNo;
  sheet.getRange(`M5:M${items.length + 4}`).dataValidation = {
    rule: { type: "list", values: ["member", "host", "caller", "other", "mixed", "uncertain"] },
  };
  sheet.getRange(`O5:O${items.length + 4}`).dataValidation = {
    rule: { type: "list", values: ["lower_third", "audible_introduction", "both", "neither", "conflicting"] },
  };
  sheet.getRange(`P5:P${items.length + 4}`).dataValidation = {
    rule: { type: "list", values: ["yes", "no", "uncertain", "not_scored"] },
  };
  sheet.getRange(`Q5:Q${items.length + 4}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 10 },
  };
  sheet.getRange(`R5:R${items.length + 4}`).dataValidation = yesNo;
  sheet.getRange(`S5:S${items.length + 4}`).dataValidation = {
    rule: { type: "list", values: ["synchronized_same_speaker", "complementary_offscreen", "reaction_shot", "mismatched", "uncertain"] },
  };
  sheet.getRange(`T5:T${items.length + 4}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 5 },
  };
  sheet.getRange(`V5:V${items.length + 4}`).dataValidation = yesNo;
  sheet.getRange(`V5:V${items.length + 4}`).conditionalFormats.add("containsText", {
    text: "yes",
    format: { fill: "#DFF1E3", font: { color: "#1B5E20", bold: true } },
  });
  sheet.tables.add(`A4:V${items.length + 4}`, true, tableName);
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(1);
  sheet.getRange("A:A").format.columnWidth = 10;
  sheet.getRange("B:C").format.columnWidth = 43;
  sheet.getRange("D:H").format.columnWidth = 13;
  sheet.getRange("I:P").format.columnWidth = 20;
  sheet.getRange("Q:T").format.columnWidth = 15;
  sheet.getRange("U:U").format.columnWidth = 32;
  sheet.getRange("V:V").format.columnWidth = 13;
}
buildCoderSheet(coderA, "CoderACasesTable", "Coder A");
buildCoderSheet(coderB, "CoderBCasesTable", "Coder B");

const eventHeaders = [
  "case_id", "event_slot", "modality", "event_type", "start_sec",
  "end_sec", "description", "target_involved", "confidence", "event_complete",
];
const eventRows = items.flatMap((item) =>
  Array.from({ length: 6 }, (_, index) => [
    item.case_id, index + 1, "", "", "", "", "", "", "", "",
  ]),
);
function buildEventSheet(sheet, tableName, coderName) {
  titleBand(
    sheet,
    `${coderName} — Observable Events`,
    "Up to six time-local events per case. Leave unused slots blank; never replace observations with trait or intent labels.",
    "J",
  );
  sheet.getRange("A4:J4").values = [eventHeaders];
  sheet.getRange(`A5:J${eventRows.length + 4}`).values = eventRows;
  styleHeader(sheet, "A4:J4");
  styleBody(sheet, `A5:J${eventRows.length + 4}`);
  sheet.getRange(`C5:C${eventRows.length + 4}`).dataValidation = {
    rule: { type: "list", values: ["audio", "visual", "audiovisual"] },
  };
  sheet.getRange(`D5:D${eventRows.length + 4}`).dataValidation = {
    rule: {
      type: "list",
      values: [
        "speech_start", "speech_end", "pause", "overlap", "interruption",
        "repair_restart", "filler", "laughter", "rate_shift", "volume_shift",
        "pitch_shift", "gaze_camera", "gaze_away", "head_nod", "head_shake",
        "hand_gesture", "facial_change", "posture_shift", "lower_third_change",
        "shot_change", "lip_sync_confirmed", "reaction_while_other_speaks",
        "offscreen_speech", "possible_av_mismatch",
      ],
    },
  };
  sheet.getRange(`E5:F${eventRows.length + 4}`).format.numberFormat = "0.0";
  sheet.getRange(`H5:H${eventRows.length + 4}`).dataValidation = {
    rule: { type: "list", values: ["yes", "no"] },
  };
  sheet.getRange(`I5:I${eventRows.length + 4}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 5 },
  };
  sheet.getRange(`J5:J${eventRows.length + 4}`).dataValidation = {
    rule: { type: "list", values: ["yes", "no"] },
  };
  sheet.tables.add(`A4:J${eventRows.length + 4}`, true, tableName);
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(2);
  sheet.getRange("A:B").format.columnWidth = 11;
  sheet.getRange("C:D").format.columnWidth = 24;
  sheet.getRange("E:F").format.columnWidth = 12;
  sheet.getRange("G:G").format.columnWidth = 44;
  sheet.getRange("H:J").format.columnWidth = 15;
}
buildEventSheet(eventsA, "CoderAEventsTable", "Coder A");
buildEventSheet(eventsB, "CoderBEventsTable", "Coder B");

// Sealed identity/source key.
titleBand(
  identity,
  "SEALED — Identity and Source Key",
  "Do not open during independent coding. Adjudicator use only after both coder sheets are locked.",
  "M",
);
identity.getRange("A3:M3").merge();
identity.getRange("A3").values = [["OPENING THIS SHEET EARLY INVALIDATES BLIND IDENTITY CODING."]];
identity.getRange("A3:M3").format = {
  fill: paleRed,
  font: { bold: true, color: "#8B1E1E" },
  horizontalAlignment: "center",
};
const keyHeaders = [
  "case_id", "expected_member", "bioguide", "program_id", "source_date",
  "source_title", "source_url", "source_speaker_label", "target_turn_seq",
  "target_transcript", "label_provenance", "sample_tier", "risk_flags",
];
identity.getRange("A4:M4").values = [keyHeaders];
identity.getRange(`A5:M${items.length + 4}`).values = items.map((item) => [
  item.case_id, item.expected_member, item.bioguide, item.program_id, item.date,
  item.title, item.source_url, item.source_speaker_label, item.target_turn_seq,
  item.target_transcript, item.label_provenance, item.label_risk_tier,
  item.label_risk_flags.join("; "),
]);
styleHeader(identity, "A4:M4");
styleBody(identity, `A5:M${items.length + 4}`);
identity.tables.add(`A4:M${items.length + 4}`, true, "IdentityKeyTable");
identity.freezePanes.freezeRows(4);
identity.freezePanes.freezeColumns(1);
identity.getRange("A:E").format.columnWidth = 14;
identity.getRange("F:F").format.columnWidth = 42;
identity.getRange("G:G").format.columnWidth = 52;
identity.getRange("H:I").format.columnWidth = 20;
identity.getRange("J:K").format.columnWidth = 56;
identity.getRange("L:M").format.columnWidth = 22;

// Adjudication sheet.
titleBand(
  adjudication,
  "Adjudication",
  "Formula-linked coder comparison. Resolve every REVIEW row after independent coding; manual final fields are gold-reference candidates.",
  "AC",
);
adjudication.getRange("A3:F3").values = [[
  "Total cases", 150, "Ready without disagreement", "", "Rows needing review", "",
]];
adjudication.getRange("D3").formulas = [["=COUNTIF(S5:S154,\"READY\")"]];
adjudication.getRange("F3").formulas = [["=COUNTIF(S5:S154,\"REVIEW\")"]];
adjudication.getRange("A3:F3").format = {
  fill: paleGold,
  font: { bold: true, color: ink },
  borders: { preset: "all", style: "thin", color: grid },
};
const adjudicationHeaders = [
  "case_id", "expected_member", "A_complete", "B_complete",
  "A_turn_owner", "B_turn_owner", "owner_agreement",
  "A_identity_name", "B_identity_name", "identity_agreement",
  "A_av_relation", "B_av_relation", "av_agreement",
  "A_speaker_count", "B_speaker_count", "speaker_count_agreement",
  "A_media_playable", "B_media_playable", "review_flag",
  "final_media_admission", "final_target_turn_owner",
  "final_observed_identity_name", "expected_identity_match",
  "final_speaker_count", "final_offscreen_speech", "final_av_relation",
  "final_disposition", "adjudication_rationale", "adjudicator_complete",
];
adjudication.getRange("A4:AC4").values = [adjudicationHeaders];
adjudication.getRange(`A5:A${items.length + 4}`).values = items.map((item) => [item.case_id]);
for (let index = 0; index < items.length; index += 1) {
  const row = index + 5;
  adjudication.getRange(`B${row}:S${row}`).formulas = [[
    `='Identity Key'!B${row}`,
    `=IF('Coder A Cases'!V${row}="","",'Coder A Cases'!V${row})`,
    `=IF('Coder B Cases'!V${row}="","",'Coder B Cases'!V${row})`,
    `=IF('Coder A Cases'!M${row}="","",'Coder A Cases'!M${row})`,
    `=IF('Coder B Cases'!M${row}="","",'Coder B Cases'!M${row})`,
    `=IF(OR(C${row}<>"yes",D${row}<>"yes"),"INCOMPLETE",IF(E${row}=F${row},"AGREE","REVIEW"))`,
    `=IF('Coder A Cases'!N${row}="","",'Coder A Cases'!N${row})`,
    `=IF('Coder B Cases'!N${row}="","",'Coder B Cases'!N${row})`,
    `=IF(OR(C${row}<>"yes",D${row}<>"yes"),"INCOMPLETE",IF(H${row}=I${row},"AGREE","REVIEW"))`,
    `=IF('Coder A Cases'!S${row}="","",'Coder A Cases'!S${row})`,
    `=IF('Coder B Cases'!S${row}="","",'Coder B Cases'!S${row})`,
    `=IF(OR(C${row}<>"yes",D${row}<>"yes"),"INCOMPLETE",IF(K${row}=L${row},"AGREE","REVIEW"))`,
    `=IF('Coder A Cases'!Q${row}="","",'Coder A Cases'!Q${row})`,
    `=IF('Coder B Cases'!Q${row}="","",'Coder B Cases'!Q${row})`,
    `=IF(OR(C${row}<>"yes",D${row}<>"yes"),"INCOMPLETE",IF(N${row}=O${row},"AGREE","REVIEW"))`,
    `=IF('Coder A Cases'!F${row}="","",'Coder A Cases'!F${row})`,
    `=IF('Coder B Cases'!F${row}="","",'Coder B Cases'!F${row})`,
    `=IF(AND(G${row}="AGREE",J${row}="AGREE",M${row}="AGREE",P${row}="AGREE",Q${row}="yes",R${row}="yes"),"READY","REVIEW")`,
  ]];
}
styleHeader(adjudication, "A4:AC4");
styleBody(adjudication, `A5:AC${items.length + 4}`);
adjudication.getRange(`S5:S${items.length + 4}`).conditionalFormats.add("containsText", {
  text: "REVIEW",
  format: { fill: paleRed, font: { color: "#8B1E1E", bold: true } },
});
adjudication.getRange(`S5:S${items.length + 4}`).conditionalFormats.add("containsText", {
  text: "READY",
  format: { fill: "#DFF1E3", font: { color: "#1B5E20", bold: true } },
});
adjudication.getRange(`T5:T${items.length + 4}`).dataValidation = {
  rule: { type: "list", values: ["admit", "exclude"] },
};
adjudication.getRange(`U5:U${items.length + 4}`).dataValidation = {
  rule: { type: "list", values: ["member", "host", "caller", "other", "mixed", "uncertain"] },
};
adjudication.getRange(`W5:W${items.length + 4}`).dataValidation = {
  rule: { type: "list", values: ["yes", "no", "uncertain", "not_scored"] },
};
adjudication.getRange(`X5:X${items.length + 4}`).dataValidation = {
  rule: { type: "whole", operator: "between", formula1: 1, formula2: 10 },
};
adjudication.getRange(`Y5:Y${items.length + 4}`).dataValidation = {
  rule: { type: "list", values: ["yes", "no"] },
};
adjudication.getRange(`Z5:Z${items.length + 4}`).dataValidation = {
  rule: { type: "list", values: ["synchronized_same_speaker", "complementary_offscreen", "reaction_shot", "mismatched", "uncertain"] },
};
adjudication.getRange(`AA5:AA${items.length + 4}`).dataValidation = {
  rule: { type: "list", values: ["gold_admit", "exclude", "needs_source_recheck"] },
};
adjudication.getRange(`AC5:AC${items.length + 4}`).dataValidation = {
  rule: { type: "list", values: ["yes", "no"] },
};
adjudication.tables.add(`A4:AC${items.length + 4}`, true, "AdjudicationTable");
adjudication.freezePanes.freezeRows(4);
adjudication.freezePanes.freezeColumns(2);
adjudication.getRange("A:B").format.columnWidth = 18;
adjudication.getRange("C:S").format.columnWidth = 17;
adjudication.getRange("T:AA").format.columnWidth = 22;
adjudication.getRange("AB:AB").format.columnWidth = 48;
adjudication.getRange("AC:AC").format.columnWidth = 18;

// Controlled vocabulary reference.
titleBand(
  lists,
  "Controlled Vocabulary Reference",
  "Definitions are abbreviated here; HUMAN_ANNOTATION_CODEBOOK.md is authoritative.",
  "H",
);
lists.getRange("A4:H4").values = [[
  "field", "allowed values", "field", "allowed values",
  "field", "allowed values", "event modality", "event examples",
]];
styleHeader(lists, "A4:H4");
lists.getRange("A5:H12").values = [
  ["yes/no", "yes; no", "turn owner", "member; host; caller; other; mixed; uncertain", "identity evidence", "lower_third; audible_introduction; both; neither; conflicting", "audio", "pause; overlap; interruption; repair_restart; filler; laughter"],
  ["confidence", "1 (low) – 5 (high)", "A/V relation", "synchronized_same_speaker; complementary_offscreen; reaction_shot; mismatched; uncertain", "identity consistency", "yes; no; uncertain; not_scored", "visual", "gaze; nod; shake; gesture; facial_change; posture_shift; shot_change"],
  ["disposition", "gold_admit; exclude; needs_source_recheck", "media admission", "admit; exclude", "complete", "yes only after review", "audiovisual", "lip_sync_confirmed; reaction_while_other_speaks; offscreen_speech; possible_av_mismatch"],
  ["", "", "", "", "", "", "", ""],
  ["Do not code", "Big Five; personality; diagnosis; honesty; motive; intent", "", "", "", "", "", ""],
  ["Normal production", "Reaction shots, graphics, and offscreen guest audio are not automatically mismatches.", "", "", "", "", "", ""],
  ["Timing", "Seconds from supplied clip, one decimal place when possible.", "", "", "", "", "", ""],
  ["Unused event", "Leave the entire event slot blank.", "", "", "", "", "", ""],
];
styleBody(lists, "A5:H12");
lists.getRange("A:H").format.columnWidth = 25;
lists.getRange("B:B").format.columnWidth = 40;
lists.getRange("D:D").format.columnWidth = 54;
lists.getRange("F:F").format.columnWidth = 48;
lists.getRange("H:H").format.columnWidth = 58;
lists.freezePanes.freezeRows(4);

// Compact inspections before export.
const sheetInspect = await workbook.inspect({
  kind: "sheet,table",
  maxChars: 8000,
  tableMaxRows: 2,
  tableMaxCols: 8,
  tableMaxCellChars: 60,
});
console.log(sheetInspect.ndjson);
const formulaInspect = await workbook.inspect({
  kind: "formula",
  sheetId: "Adjudication",
  range: "B3:S12",
  maxChars: 8000,
  options: { maxResults: 120 },
});
console.log(formulaInspect.ndjson);
const formulaErrorInspect = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  maxChars: 4000,
  options: { useRegex: true, matchFormulas: true, maxResults: 50 },
});
console.log(formulaErrorInspect.ndjson);
if (!formulaErrorInspect.ndjson.includes("matched 0 entries")) {
  throw new Error(`Formula error scan failed:\n${formulaErrorInspect.ndjson}`);
}

// Render every sheet for visual QA. Very long coding sheets are scaled down but
// are rendered through representative top ranges to keep the image bounded.
const previewRanges = {
  "README": "A1:H18",
  "Case Register": "A1:J24",
  "Coder A Cases": "A1:V18",
  "Coder A Events": "A1:J24",
  "Coder B Cases": "A1:V18",
  "Coder B Events": "A1:J24",
  "Identity Key": "A1:M18",
  "Adjudication": "A1:AC18",
  "Lists": "A1:H12",
};
for (const sheetName of [
  "README", "Case Register", "Coder A Cases", "Coder A Events",
  "Coder B Cases", "Coder B Events", "Identity Key", "Adjudication", "Lists",
]) {
  const preview = await workbook.render({
    sheetName,
    range: previewRanges[sheetName],
    scale: 0.55,
    format: "png",
  });
  const safeName = sheetName.toLowerCase().replaceAll(" ", "_");
  await fs.writeFile(
    path.join(previewDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const output = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = path.join(outputDir, "interview_av_validation_150.xlsx");
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, previews: previewDir, cases: items.length }, null, 2));
