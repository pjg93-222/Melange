/* F4 tests added to the two suites that already own these files. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\tests',
  bak: '.bak-20260914-Fc',
  eol: 'lf',
  files: [
    {
      path: 'test_chart_studio_contributions.cjs',
      eol: 'lf',
      edits: [
        {
          find: "test('drill-through keeps exact ZIP and all selected raw state variants'",
          replace: "test('reconcile names why Graph and Studio differ, and says so plainly when they do not',()=>{\n" +
            " const base={totals:{amount:1209041200},comparison:{receipt:1209041200},provenance:{workbook_sha256:'w'.repeat(64)},reconciliation:{aggregate_filters_applied:false}};\n" +
            " const graph={totals:{giving:12090412},reports:[{name:'Banking.xlsx',sha256:'w'.repeat(64)}]};\n" +
            " const clean={tier:'',funding:'all'},wider=amount=>({...base,totals:{amount}});\n" +
            " const agree=studio.reconcile(base,'receipt',graph,clean);\n" +
            " assert.equal(agree.agree,true);assert.equal(agree.graphCents,1209041200);assert.equal(agree.studioCents,1209041200);\n" +
            " assert.equal(agree.differenceCents,0);assert.equal(agree.reason,'');\n" +
            " // A different basis is a different question, so the strip must not call it agreement.\n" +
            " const basis=studio.reconcile(wider(990000000),'original_observed',graph,clean);\n" +
            " assert.equal(basis.agree,false);assert.equal(basis.reasonId,'basis');assert.match(basis.reason,/Published included receipts/);\n" +
            " // A Graph employee-level or giving-type filter has no verified field, so the Studio total is the wider one.\n" +
            " assert.equal(studio.reconcile(wider(1300000000),'receipt',graph,{tier:'Chief',funding:'all'}).reasonId,'graph_filter');\n" +
            " assert.equal(studio.reconcile(wider(1300000000),'receipt',graph,{tier:'',funding:'personal'}).reasonId,'graph_filter');\n" +
            " // Two different workbooks are not reconcilable by arithmetic.\n" +
            " assert.equal(studio.reconcile(wider(1300000000),'receipt',{...graph,reports:[{sha256:'z'.repeat(64)}]},clean).reasonId,'workbook');\n" +
            " assert.equal(studio.reconcile({...wider(1300000000),reconciliation:{aggregate_filters_applied:true}},'receipt',graph,clean).reasonId,'aggregate');\n" +
            " const unexplained=studio.reconcile(wider(1300000000),'receipt',graph,clean);\n" +
            " assert.equal(unexplained.reasonId,'unexplained');assert.equal(unexplained.differenceCents,90958800);\n" +
            " // No Graph total is an absence, never a difference to explain.\n" +
            " assert.equal(studio.reconcile(base,'receipt',null,clean).reasonId,'unavailable');\n" +
            " assert.equal(studio.reconcile(base,'receipt',{totals:{}},clean).reasonId,'unavailable');\n" +
            " assert.equal(studio.reconcile({totals:{}},'receipt',graph,clean).reasonId,'unavailable');\n" +
            "});\n" +
            "test('drill-through keeps exact ZIP and all selected raw state variants'"
        }
      ]
    },
    {
      path: 'test_cross_reference_view.cjs',
      eol: 'lf',
      edits: [
        {
          find: "assert.match(view.html({available:true,status:'running',run_id:'active',progress:{steps:[{id:'collect',status:'running'}]}}),/In progress/);",
          replace: "assert.match(view.html({available:true,status:'running',run_id:'active',progress:{steps:[{id:'collect',status:'running'}]}}),/In progress/);\n\n" +
            "// Every dollar metric names the cycles it describes; a count metric does not.\n" +
            "assert.match(rendered,/Observed original giving<\\/span><strong>\\$100\\.00<\\/strong><small class=\"xref-metric-cycles\">Cycles 2024<\\/small>/);\n" +
            "assert.match(rendered,/Observed PAC outgoing activity<\\/span><strong>\\$60\\.00<\\/strong><small class=\"xref-metric-cycles\">Cycles 2024<\\/small>/);\n" +
            "assert.match(rendered,/Previous receipt total<\\/span><strong>\\$160\\.00<\\/strong><small class=\"xref-metric-cycles\">Cycles 2024<\\/small>/);\n" +
            "assert.match(rendered,/Change from previous total<\\/span><strong>-\\$60\\.00<\\/strong><small class=\"xref-metric-cycles\">Cycles 2024<\\/small>/);\n" +
            "assert.doesNotMatch(rendered,/Records examined<\\/span><strong>5<\\/strong><small class=\"xref-metric-cycles\"/);\n" +
            "assert.doesNotMatch(rendered,/Records needing review<\\/span><strong>1<\\/strong><small class=\"xref-metric-cycles\"/);\n" +
            "// A run with no scope cycles states no cycles rather than the previous run's.\n" +
            "const noCycles = structuredClone(fixture);\n" +
            "noCycles.report.scope.cycles = [];\n" +
            "assert.doesNotMatch(view.html(noCycles),/xref-metric-cycles/);\n\n" +
            "// The $0 caption says which reviews leave money out of every total above.\n" +
            "assert.match(rendered,/Rows with an unresolved company attribution are counted at \\$0 in every total above; memo, transfer, earmark and role reviews stay inside Observed original giving until resolved\\./);\n\n" +
            "// Engine reason keys are shown in plain words wherever a reason is printed.\n" +
            "const named = structuredClone(fixture);\n" +
            "named.report.unresolved_reasons = [{reason:'company_attribution_unresolved',records:2,amount:80}];\n" +
            "named.report.review_queue = [{company:'A Bank',reason:'earmark_destination_ambiguous',cycle:2024,amount:40,record_id:'123'}];\n" +
            "named.report.changes = [{company:'A Bank',reason:'linked_refund',cycle:2024,before:160,after:100,delta:-60,record_id:'456'}];\n" +
            "named.report.coverage_reasons = [{reason:'latest_filing_manifest_not_corroborated',records:1,amount:10,action:'Check the manifest.'}];\n" +
            "Object.assign(named.report.summary,{coverage_records:1,coverage_amount:10});\n" +
            "const namedHtml = view.html(named);\n" +
            "assert.match(namedHtml,/Donor not yet matched to a listed company \\(counted at \\$0\\)/);\n" +
            "assert.match(namedHtml,/Earmark destination ambiguous/);\n" +
            "assert.match(namedHtml,/Linked refund adjustment/);\n" +
            "assert.match(namedHtml,/Latest filing not corroborated by its manifest/);\n" +
            "assert.doesNotMatch(namedHtml,/company_attribution_unresolved|earmark_destination_ambiguous|latest_filing_manifest_not_corroborated/);\n" +
            "// The reason names the engine already had keep the meaning they had.\n" +
            "const kept = structuredClone(fixture);\n" +
            "kept.report.unresolved_reasons = [{reason:'memo_parent_ambiguous',records:1,amount:5}];\n" +
            "assert.match(view.html(kept),/Memo points to more than one possible receipt/);"
        }
      ]
    }
  ]
};
