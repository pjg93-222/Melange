'use strict';
// Compiled, closed data-only channel. These values never come from settings,
// a renderer, or downloaded metadata. Public module-v1 stays independent.
const MiB=1024**2;
const role=(path,maxBytes)=>Object.freeze({path,maxBytes});
const WORKSPACE_KINDS=Object.freeze({
 melange:Object.freeze(['melange.dashboard-pages.v1','melange.staffer-display-graph.v1','melange.payroll-identity-core.v1','melange.industry-pages.v1','melange.staffer-analysis.v1']),
 mentat:Object.freeze(['mentat.aggregate-forecast-core.v1','mentat.report-analysis.v1'])
});
const DASHBOARD_ROLES=Object.freeze({
 network:role('dashboard/network.json',32*MiB),members:role('dashboard/members.json',32*MiB),
 'member-profiles':role('dashboard/member-profiles.json',96*MiB),industry:role('dashboard/industry.json',16*MiB),
 'staffer-summary':role('dashboard/staffer-summary.json',MiB),'staffer-offices':role('dashboard/staffer-offices.json',16*MiB),
 'staffer-organisations':role('dashboard/staffer-organisations.json',16*MiB),'staffer-clients':role('dashboard/staffer-clients.json',16*MiB)
});
const CHANNEL=Object.freeze({id:'workspace-v1',cacheName:'github-workspace-data',pointerBranch:'desktop-workspace-data',pointerPath:'docs/desktop-workspace/current.json',
 sourceField:'ownerGitHubWorkspaceData',localStateKind:'github-workspace-local-state',managedStateKind:'github-workspace-state'});
const APPS=Object.freeze({
 melange:Object.freeze({repository:'pjg93-222/melange',purpose:'melange-full-workspace-data'}),
 mentat:Object.freeze({repository:'pjg93-222/mentat',purpose:'mentat-full-workspace-data'})
});
const REPORT_SLUGS=Object.freeze(['banking','credit_union','property_casualty_insurance','telecom','community_banks','credit_arms','fintech','crypto']);
const ARCHIVES=Object.freeze({
 'melange.industry-pages.v1':Object.freeze({members:Object.freeze(['champions.json','forecast.json','bills.json','screen.json','interactions.json','derivation.json']),maxDecodedBytes:256*MiB}),
 'melange.staffer-analysis.v1':Object.freeze({members:Object.freeze([
  'source/catalog.sqlite','source/receipt.json','lda/catalog.sqlite','lda/receipt.json',
  'activity/index.sqlite','activity/receipt.json','activity/pin.json',
  'profiles/records.ndjson','profiles/receipt.json','profiles/checkpoint.json','identity/references.json','contacts/directory.json','derivation.json'
 ]),maxDecodedBytes:24*1024**3}),
 'mentat.report-analysis.v1/reports':Object.freeze({members:Object.freeze(['credit-arms.xlsx','fintech.xlsx','crypto.xlsx','derivation.json']),maxDecodedBytes:256*MiB}),
 'mentat.report-analysis.v1/facts':Object.freeze({members:Object.freeze([...REPORT_SLUGS.flatMap(slug=>[slug+'/index.sqlite',slug+'/receipt.json']),'derivation.json']),maxDecodedBytes:16*1024**3})
});
function configuration(appId){if(!Object.hasOwn(APPS,appId))throw new Error('Unsupported workspace-data application.');return APPS[appId];}
function roleMaps(){
 // Lazy import keeps the shared public protocol independent of registry code.
 const core=require('./module-data-adapters.cjs').ROLE_MAPS;
 return Object.freeze({'melange.dashboard-pages.v1':DASHBOARD_ROLES,
  'melange.staffer-display-graph.v1':core['melange.staffer-graph-core.v1'],
  'melange.payroll-identity-core.v1':core['melange.payroll-identity-core.v1'],
  'mentat.aggregate-forecast-core.v1':core['mentat.aggregate-forecast-core.v1'],
  'melange.industry-pages.v1':Object.freeze({pages:role('industry/pages.data.zip',64*MiB)}),
  'melange.staffer-analysis.v1':Object.freeze({records:role('staffer/analysis.data.zip',4*1024**3)}),
  'mentat.report-analysis.v1':Object.freeze({'supplemental-reports':role('analysis/reports.data.zip',64*MiB),facts:role('analysis/facts.data.zip',2*1024**3)})});
}
module.exports={WORKSPACE_KINDS,DASHBOARD_ROLES,REPORT_SLUGS,ARCHIVES,CHANNEL,configuration,roleMaps};
