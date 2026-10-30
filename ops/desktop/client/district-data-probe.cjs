'use strict';
// A negative data verdict grants no application health. It is accepted only
// from the current compiled program and this exact signed-roster invocation.
const crypto=require('node:crypto');
const {canonical}=require('./access-client.cjs');
const {ROLES,IDS,MAX_FILE}=require('./github-district-protocol.cjs');
const {DISTRICT_PROGRAM_SPECS}=require('./module-application-inventory.cjs');
const {verifyProgram}=require('./module-data-runtime-boundary.cjs');
const {prepareDesktopProbe}=require('./desktop-probe.cjs');
const {dataStartupFailure,isDataStartupFailure,programFailure}=require('./startup-failure.cjs');
const exact=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|');
function districtSourceDigest(district,files){
 if(!IDS.includes(district)||!Array.isArray(files)||files.length<ROLES.length||files.length>10000)throw programFailure();
 const rows=files.map(row=>{
  const snapshot=/^snapshots\/(?:co-cd005|or-cd005|ct-cd001)-[a-f0-9]{12}\/(?:(?:manifest|rows|geometry|area_indices|adjacency)\.json|(?:streets|district)\.geojson|derived\/[A-Za-z0-9_-]+\.json(?:\.gz)?)$/;
  if(!exact(row,['role','path','bytes','sha256'])||(!ROLES.includes(row.role)&&!snapshot.test(row.role))||row.path!==district+'/data/'+row.role||!Number.isSafeInteger(row.bytes)||row.bytes<=0||row.bytes>MAX_FILE||typeof row.sha256!=='string'||!/^[a-f0-9]{64}$/.test(row.sha256))throw programFailure();
  return {...row};
 }).sort((a,b)=>a.role<b.role?-1:1);
 if(new Set(rows.map(row=>row.role)).size!==rows.length||ROLES.some(role=>!rows.some(row=>row.role===role))||rows.reduce((sum,row)=>sum+row.bytes,0)>12*1024**3)throw programFailure();
 return crypto.createHash('sha256').update(canonical({district,files:rows})).digest('hex');
}
function verifyDistrictProgram(runtime,sourceRoot){
 const contract=DISTRICT_PROGRAM_SPECS?.terrier;
 try{const roots=verifyProgram(runtime,contract);if(sourceRoot!==undefined&&roots.source!==sourceRoot)throw programFailure();return contract;}catch{throw programFailure();}
}
function prepareDistrictProbe({runtime,command,sourceRoot,dataRoot,district,files,signal,onDiagnostic}){
 const contract=verifyDistrictProgram(runtime,sourceRoot),guard=()=>verifyDistrictProgram(runtime,sourceRoot);
 guard();
 const context=Object.freeze({launchNonce:crypto.randomBytes(32).toString('base64url'),programFingerprint:contract.programFingerprint,sourceDigest:districtSourceDigest(district,files)});
 const reader=prepareDesktopProbe(command,'--desktop-github-district-check',{signal,onDiagnostic,beforeSpawn:guard,
  classifyFailure(value){
   if(!exact(value,['error','dataBlocked','errorKind','district','nativeDiagnostic'])||value.error!=='The selected district data could not be verified.'||value.dataBlocked!==true||!['integrity','storage'].includes(value.errorKind)||value.district!==district||!exact(value.nativeDiagnostic,Object.keys(context))||canonical(value.nativeDiagnostic)!==canonical(context))return null;
   guard();return dataStartupFailure({reason:value.errorKind});
  }});
 return Object.freeze({async run(){
  try{guard();const value=await reader.run({sourceRoot,dataRoot,district,nativeDiagnostic:context});guard();if(!exact(value,['validated','district'])||value.validated!==true||value.district!==district)throw programFailure();return true;}
  catch(error){if(signal?.aborted)throw error;guard();if(isDataStartupFailure(error))throw error;throw programFailure();}
 },cancel:()=>reader.cancel()});
}
module.exports={prepareDistrictProbe,districtSourceDigest,verifyDistrictProgram};
