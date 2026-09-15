/* F5 and the wording half of F4: the console names its own controls. There is
   no "contribution explorer" in this console - the control is Data source - and
   the default empty state names the mode the console actually starts in. Read
   from the shipped files and the pure modules, so a regression anywhere in the
   client is caught without a browser. */
'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const app=path.join(__dirname,'../app');
const core=require(path.join(app,'chart-studio-core.js'));
const contributions=require(path.join(app,'chart-studio-contributions.js'));
const read=name=>fs.readFileSync(path.join(app,name),'utf8');

const COLUMNS=[{index:0,name:'Recipient Category',type:'category'},
  {index:1,name:'Amount',type:'number'},{index:2,name:'Contribution Count',type:'number'}];
const sheet=patch=>Object.assign(core.createSheet('Sheet 1','s1'),patch||{});
const issues=patch=>core.compileReport(sheet(patch),COLUMNS).issues.join(' ');
const notes=patch=>core.compileReport(sheet(patch),COLUMNS).notes.join(' ');

const CATALOG=[...['company','cycle','recipient'].map(id=>({id,label:id,role:'dimension'})),
  ...['amount','records'].map(id=>({id,label:id,role:'measure',unit:id==='records'?'count':'cents'}))];
const VERIFIED=contributions.fields(CATALOG);
const at=id=>VERIFIED.find(f=>f.id===id).index;
const compile=state=>contributions.compile(state,VERIFIED,{dataset:'Banking',basis:'receipt'});

test('no refusal points at a "contribution explorer" this console does not have',()=>{
  for(const name of ['chart-studio-core.js','chart-studio.js','chart-studio-contributions.js','index.html','chart-studio.css'])
    assert.doesNotMatch(read(name),/contribution explorer/i,name+' still names a control that does not exist');
});

test('an empty sheet asks for a grouping and a dollar measure, in those words',()=>{
  assert.match(issues({}),/Add a grouping \(company, recipient, cycle\) and a dollar measure\./);
  assert.match(issues({marks:Object.assign(core.createSheet('x').marks,{type:'bar'})}),
    /Add a grouping \(company, recipient, cycle\) and a dollar measure\./);
  assert.doesNotMatch(issues({}),/Drag a dimension/);
});

test('every worksheet refusal names the Data source control as the way on',()=>{
  const marks=patch=>Object.assign(core.createSheet('x').marks,patch);
  assert.match(issues({marks:marks({size:{column:1,aggregation:'sum'}})}),
    /Size field encoding is unavailable in the worksheet renderer\. Switch Data source to Verified contributions, or remove this field\./);
  assert.match(issues({columns:[{column:0,aggregation:'sum'}],
    rows:[{column:1,aggregation:'sum'},{column:2,aggregation:'sum'}]}),
    /Use a two-measure scatter, separate sheets, or switch Data source to Verified contributions\./);
  assert.match(issues({marks:marks({type:'circle'}),columns:[{column:1,aggregation:'sum'}],
    rows:[{column:2,aggregation:'sum'},{column:0,aggregation:'sum'}]}),
    /dimension and Detail grouping need Data source: Verified contributions\./);
  assert.match(notes({columns:[{column:0,aggregation:'sum'}],rows:[{column:1,aggregation:'sum'}],
    filters:[{column:1,op:'gte',value:'5'}]}),
    /Aggregate measure filters are available in Verified contributions\./);
});

test('the verified engine asks for a measure and a mark in the reader’s vocabulary',()=>{
  const bare=Object.assign(core.createSheet('a'),{columns:[{column:at('company'),aggregation:'sum'}]});
  assert.throws(()=>compile(bare),/^Error: Add a dollar or count measure to Rows or Columns\.$/);
  const odd=Object.assign(core.createSheet('b'),{columns:[{column:at('company'),aggregation:'sum'}],
    rows:[{column:at('amount'),aggregation:'sum'}]});
  odd.marks.type='sunburst';
  assert.throws(()=>compile(odd),/^Error: This chart type needs individual receipts\. Switch Data source to Report worksheet, or select Bar, Line, Circle, Text or Map\.$/);
});

test('the default empty state names the mode the console starts in',()=>{
  const html=read('index.html');
  assert.match(html,/<p id="studio-note" class="studio-note">Choose a verified report in the Data panel to begin\.<\/p>/);
  assert.doesNotMatch(html,/Choose a report worksheet in the Data panel to begin\.<\/p>/);
  // The two runtime empty states agree with it, each naming its own mode.
  const js=read('chart-studio.js');
  assert.match(js,/el\('note'\)\.textContent='Choose a verified report in the Data panel to begin\.';/);
  assert.match(js,/el\('note'\)\.textContent = 'Choose a report worksheet in the Data panel to begin\.';/);
  assert.doesNotMatch(js,/in the Data pane\b/);
});

test('the header keeps a permanent, plainly named way back to the report picker',()=>{
  const html=read('index.html');
  assert.match(html,/<button id="studio-scope-change" class="studio-scope-change" type="button" title="[^"]*">Data source<\/button>/);
  assert.doesNotMatch(html,/id="studio-scope-change"[^>]*\shidden/);
  assert.match(html,/<details class="studio-source-disclosure" id="studio-source-details" open>/);
});

test('Graph names the figure it shows, so it can be matched to Chart Studio',()=>{
  assert.match(read('index.html'),/<strong id="graph-total">—<\/strong><small id="graph-basis-note"><\/small>/);
  assert.match(read('graph.js'),
    /Workbook included receipts, net\. Same figure as Chart Studio’s Published included receipts basis\./);
});

test('the group limit says what forty means, and stays forty',()=>{
  assert.strictEqual(core.STUDIO_GROUP_LIMIT,40);
  const label='40 per page (verified) · fold after 40 (worksheet); Graph and classic fold at 60';
  assert.match(read('index.html'),/title="40 per page \(verified\) &#183; fold after 40 \(worksheet\); Graph and classic fold at 60"/);
  assert.ok(read('chart-studio.js').includes(label),'the verified label says the same thing as the markup');
  assert.doesNotMatch(read('index.html'),/default 40/);
  // The page counter says the totals are not the page.
  assert.match(read('chart-studio.js'),/groups · totals cover all \$\{fmt\(result\.group_count\)\}/);
});

test('the cross-reference reasons and captions are the approved plain words',()=>{
  const xref=read('cross-reference.js');
  for(const [key,label] of [
    ['company_attribution_unresolved','Donor not yet matched to a listed company (counted at $0)'],
    ['attribution_unresolved','Attribution not settled (counted at $0)'],
    ['company_attribution_not_accepted','Company match not accepted'],
    ['memo_parent_not_established','Memo entry without a proven parent receipt'],
    ['original_source_of_transfer_unresolved','Transfer whose original donor is unresolved'],
    ['earmark_counterpart_not_unique','Earmark with more than one possible counterpart'],
    ['earmark_destination_ambiguous','Earmark destination ambiguous'],
    ['overlapping_or_cyclic_earmark_links','Earmark links overlap or loop'],
    ['observed_filing_versions_unresolved','Amended filings not reconciled'],
    ['latest_filing_transaction_replacement_missing','Latest filing lacks the replacing transaction'],
    ['latest_filing_manifest_not_corroborated','Latest filing not corroborated by its manifest'],
    ['linked_refunds_exceed_original_gift','Refunds exceed the original gift'],
    ['receipt_date_missing','Receipt date missing'],
    ['excluded_source_metadata_conflict','Source metadata conflict'],
    ['superseded_in_observed_filing_family','Superseded by a later filing'],
    ['same_original_gift_at_conduit_and_destination','Same gift seen at conduit and destination'],
    ['explicit_same_filing_memo_reference','Memo references its own filing'],
    ['explicit_observed_refund','Observed refund'],
    ['linked_refund','Linked refund adjustment']
  ]) assert.ok(xref.includes(key+":'"+label.replaceAll("'","\\'")+"'"),'missing plain-word name for '+key);
  assert.ok(xref.includes('Rows with an unresolved company attribution are counted at $0 in every total above; memo, transfer, earmark and role reviews stay inside Observed original giving until resolved.'));
});

test('the reconciliation strip has a reason for every way two totals can part',()=>{
  assert.deepStrictEqual(Object.keys(contributions.RECONCILE_REASONS),
    ['basis','graph_filter','workbook','aggregate','cycle','unavailable','unexplained']);
  for(const reason of Object.values(contributions.RECONCILE_REASONS)) assert.match(reason,/^[a-z]/,'a reason reads as the tail of a sentence');
});
