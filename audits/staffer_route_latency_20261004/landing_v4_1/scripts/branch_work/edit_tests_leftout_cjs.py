"""v4.1 fix 4, the page suite (fec/tests/surfaces/test_staffer_left_out_staff.cjs): the roster wording for a directory-only comparison."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_lib import edit

PATH = r'C:\Users\pgoff\Melange-wt\route-core\fec\tests\surfaces\test_staffer_left_out_staff.cjs'

HEAD_OLD = r'''// uncovered_staff_count on every office answer; test_staffer_office_covered_staff.py asserts that against the real producer
// through the router, the service and the HTTP handler. The page shows one plain line with the result when that count is above
// zero: its singular and plural forms, and none when the count is zero or missing, or when no search ran because the origin is the person without
// coverage (the answer names the origin among unavailable_person_ids; test_staffer_office_covered_staff.py pins that on the producer). The real
// staffer-route.js runs in a vm over a small fake DOM and a scripted server. The page as it was before the change (read from git) and thirteen
// deliberate bugs of the new page are each caught by the same scenarios: the negative controls.
'''
HEAD_NEW = r'''// uncovered_staff_count on every office answer; test_staffer_office_covered_staff.py asserts that against the real producer
// through the router, the service and the HTTP handler. The page shows one plain line with the result when that count is above
// zero: its singular and plural forms, and none when the count is zero or missing, or when no search ran because the origin is the person without
// coverage (the answer names the origin among unavailable_person_ids; test_staffer_office_covered_staff.py pins that on the producer).
// The line names the coverage the staff lack as the answer's uncovered_basis says (v4.1): payroll_or_roster, or roster where the comparison reads
// directory episodes only, which has no payroll evidence to cover anyone; any other basis, or none, gets the payroll-or-roster wording. The real
// staffer-route.js runs in a vm over a small fake DOM and a scripted server. The page as it was before the change and as v4 ran it (read from git)
// and seventeen deliberate bugs of the new page are each caught by the same scenarios: the negative controls.
'''

CONST_OLD = r'''const SINGULAR="1 of this office's current staff lacks the payroll or staffer-roster coverage this model requires and was left out.";
'''
CONST_NEW = r'''const SINGULAR="1 of this office's current staff lacks the payroll or staffer-roster coverage this model requires and was left out.";
// ... and for a comparison of directory episodes only (uncovered_basis 'roster'): no payroll evidence is read there, so the roster alone is named.
const ROSTER_PLURAL=n=>`${n} of this office's current staff lack the staffer-roster coverage this model requires and were left out.`;
const ROSTER_SINGULAR="1 of this office's current staff lacks the staffer-roster coverage this model requires and was left out.";
'''

BEFORE_OLD = r'''const before=fromGit(BEFORE,REL);
const NO_GIT=before===null?'the pre-change page (commit '+BEFORE.slice(0,9)+') is not in this checkout':false;
'''
BEFORE_NEW = r'''const before=fromGit(BEFORE,REL);
const NO_GIT=before===null?'the pre-change page (commit '+BEFORE.slice(0,9)+') is not in this checkout':false;
// The page as v4 ran it: the line is there, and it names payroll whatever the basis.
const V4='79ef9f1b7440bcee21c7f7c677a93263d9fcc04a';
const v4=fromGit(V4,REL);
const NO_V4=v4===null?'the v4 page (commit '+V4.slice(0,9)+') is not in this checkout':false;
'''

SCEN_ANCHOR = r'''const SCENARIOS=[
'''
SCEN_NEW_FUNCS = r'''// The basis of the count picks the wording: 'roster' names the roster alone, in the singular and the plural, on every kind of answer that shows the line.
const ROSTER=(n,extra={})=>({uncovered_staff_count:n,uncovered_staff_ids:Array.from({length:n},(_,i)=>'u'+(i+1)),uncovered_basis:'roster',...extra});
async function namesTheRosterAloneWhereNoPayrollIsRead(code,ok){
  const cases=[['found, plural',found(ROSTER(3)),ROSTER_PLURAL(3)],['found, singular',found(ROSTER(1)),ROSTER_SINGULAR],
    ['unreachable',{...UNREACHABLE,...ROSTER(2)},ROSTER_PLURAL(2)],['coverage, no staff covered',NO_STAFF_COVERED({uncovered_basis:'roster'}),ROSTER_PLURAL(3)]];
  for(const [what,payload,expected] of cases){
    await search(code,payload,page=>{
      ok(JSON.stringify(page.leftOut())===JSON.stringify([expected]),'roster, '+what+': one line, "'+expected+'"; found '+JSON.stringify(page.leftOut()));
      ok(!/payroll/.test(page.leftOut().join(' ')),'roster, '+what+': the line does not mention payroll, found '+JSON.stringify(page.leftOut()));
    });
  }
  await search(code,found(ROSTER(3)),page=>{
    const lines=page.card()?.children.filter(c=>c.tag==='p').map(c=>c.textContent)||[];
    ok(JSON.stringify(lines.filter(l=>[COMPARED,ROSTER_PLURAL(3),RECORDS].includes(l)))===JSON.stringify([COMPARED,ROSTER_PLURAL(3),RECORDS]),'roster, card: the line sits between the compared and the records lines; found '+JSON.stringify(lines));
  });
  const second={...found(ROSTER(3)),route_rank:2};
  await search(code,{...found(ROSTER(3)),routes:[found(ROSTER(3)),second],routes_requested:3,alternative_strategy:'distinct'},page=>{
    const choices=page.$('route-options').children.filter(e=>e.tag==='button');
    choices[1]?.onclick();
    ok(JSON.stringify(page.leftOut())===JSON.stringify([ROSTER_PLURAL(3)]),'roster, routes: route 2 shows the line once, found '+JSON.stringify(page.leftOut()));
  });
  // where no search ran because the origin is the person without coverage there is still no line, whatever the basis
  await search(code,ORIGIN_UNCOVERED({uncovered_basis:'roster'}),page=>{
    ok(page.leftOut().length===0,'roster, origin uncovered: no line, found '+JSON.stringify(page.leftOut()));
  });
}
// Anything but the word 'roster' keeps the wording the page always had, so a page in front of an older server (no basis at all) says what it said.
async function keepsThePayrollOrRosterWordingForAnyOtherBasis(code,ok){
  const cases=[['payroll_or_roster',{uncovered_basis:'payroll_or_roster'}],['no basis, as an older server answers',{}],['null',{uncovered_basis:null}],
    ['an empty string',{uncovered_basis:''}],['another case',{uncovered_basis:'Roster'}],['a longer name',{uncovered_basis:'roster_only'}],['a list',{uncovered_basis:['roster']}]];
  for(const [what,extra] of cases){
    await search(code,found({uncovered_staff_count:2,uncovered_staff_ids:['u1','u2'],...extra}),page=>{
      ok(JSON.stringify(page.leftOut())===JSON.stringify([PLURAL(2)]),'basis ('+what+'): the payroll-or-roster line, found '+JSON.stringify(page.leftOut()));
    });
  }
  await search(code,found({uncovered_staff_count:1,uncovered_staff_ids:['u1'],uncovered_basis:'payroll_or_roster'}),page=>{
    ok(JSON.stringify(page.leftOut())===JSON.stringify([SINGULAR]),'basis (payroll_or_roster, singular): the singular payroll-or-roster line, found '+JSON.stringify(page.leftOut()));
  });
}
'''
SCEN_OLD = r'''  ['an answer that is not a coverage answer keeps its line',onlyACoverageAnswerLosesItsLine],
];
'''
SCEN_NEW = r'''  ['an answer that is not a coverage answer keeps its line',onlyACoverageAnswerLosesItsLine],
  ['a directory-only comparison names the staffer roster alone, in every kind of answer',namesTheRosterAloneWhereNoPayrollIsRead],
  ['any other basis, or none, keeps the payroll-or-roster wording',keepsThePayrollOrRosterWordingForAnyOtherBasis],
];
'''

WORDS_OLD = r'''  assert.ok(!/work records/.test(PLURAL(3))&&!/work records/.test(SINGULAR));
});
'''
WORDS_NEW = r'''  assert.ok(!/work records/.test(PLURAL(3))&&!/work records/.test(SINGULAR));
  // The directory-only wording (uncovered_basis 'roster'): the roster alone, and no claim about payroll.
  assert.equal(ROSTER_PLURAL(3),"3 of this office's current staff lack the staffer-roster coverage this model requires and were left out.");
  assert.equal(ROSTER_SINGULAR,"1 of this office's current staff lacks the staffer-roster coverage this model requires and was left out.");
  assert.ok(!/payroll|work records/.test(ROSTER_PLURAL(3))&&!/payroll|work records/.test(ROSTER_SINGULAR));
});
'''

CONTROL_OLD = r'''// Deliberate bugs of the new page. Each is one edit to the real file, and the scenarios must notice every one.
'''
CONTROL_NEW = r'''test('negative control: the page as v4 ran it names payroll for a directory-only comparison, and only there is it wrong',{skip:NO_V4},async()=>{
  const failures=await failuresOf(v4);
  assert.ok(failures.length>0,'it fails the roster scenario');
  assert.ok(failures.every(f=>/^roster, /.test(f)),'and nothing else: '+JSON.stringify(failures.filter(f=>!/^roster, /.test(f)).slice(0,4)));
  assert.ok(failures.some(f=>/^roster, found, plural/.test(f))&&failures.some(f=>/^roster, found, singular/.test(f)),'it names payroll in both forms');
});

// Deliberate bugs of the new page. Each is one edit to the real file, and the scenarios must notice every one.
'''

BUG2_OLD = r'''  ['the line says the staff have no work records, as it did before the coverage wording was corrected',"${left===1?'lacks':'lack'} the payroll or staffer-roster coverage this model requires","${left===1?'has':'have'} no work records this model uses",/^plural: exactly one line/],
'''
BUG2_NEW = r'''  ['the line says the staff have no work records, as it did before the coverage wording was corrected',"${left===1?'lacks':'lack'} the ${coverage} coverage this model requires","${left===1?'has':'have'} no work records this model uses",/^plural: exactly one line/],
'''

BUGS_OLD = r'''  ['the line is never held back',GUARD,"",/^origin uncovered/],
];
'''
BUGS_NEW = r'''  ['the line is never held back',GUARD,"",/^origin uncovered/],
  // The basis of the count (v4.1).
  ['the basis is ignored: every answer names payroll',"coverage=data.uncovered_basis==='roster'?'staffer-roster':'payroll or staffer-roster'","coverage='payroll or staffer-roster'",/^roster, /],
  ['the roster alone is named whatever the basis',"coverage=data.uncovered_basis==='roster'?'staffer-roster':'payroll or staffer-roster'","coverage='staffer-roster'",/^basis \(payroll_or_roster\)|^plural: exactly one line/],
  ['any basis that is set names the roster alone',"data.uncovered_basis==='roster'","data.uncovered_basis",/^basis \(payroll_or_roster\)/],
  ['the basis is read from the wrong field',"data.uncovered_basis==='roster'","data.basis==='roster'",/^roster, /],
];
'''

edit(PATH, [(HEAD_OLD, HEAD_NEW), (CONST_OLD, CONST_NEW), (BEFORE_OLD, BEFORE_NEW), (SCEN_ANCHOR, SCEN_NEW_FUNCS + SCEN_ANCHOR), (SCEN_OLD, SCEN_NEW),
            (WORDS_OLD, WORDS_NEW), (CONTROL_OLD, CONTROL_NEW), (BUG2_OLD, BUG2_NEW), (BUGS_OLD, BUGS_NEW)])
