'use strict';
// Generated, signed data and a trusted test-only installer boundary. This does
// not exercise or claim a production Runtime/Python installation contract.
const assert=require('node:assert/strict');
const {ModuleDataStartup,moduleHealthBinding}=require('../../module-data-startup.cjs');
const {GitHubModules}=require('../../github-modules.cjs');
const {refuseModuleDataSettings}=require('../../runtime.cjs');
const {environment}=require('./github-module-fixture.cjs');
function startupFixture(t,{appId='mentat',production=false,changeBoundary=()=>{},changeOptions=()=>{}}={}){
 const data=environment(appId),events=[],states=[];let selected=data.selected,generation=0,stageEligible=true;
 const runtime={child:null,origin:null,configuration:null,requestsAllowed:true,launchPath:'/',
  async start(configuration){refuseModuleDataSettings(configuration);events.push('ordinary-start');this.configuration=configuration;this.child={ordinary:true};this.origin='http://127.0.0.1:43212';return this.origin;},
  async stop(){events.push('stop');this.child=null;this.origin=null;this.configuration=null;}};
 const contract={schemaVersion:1,appId,contractId:appId+'.synthetic-complete-test.v1',programFingerprint:'a'.repeat(64),
  requiredKinds:Object.keys(data.remote.registry),registry:data.remote.registry,publicReaders:['synthetic-aggregate'],privateBoundaries:['original-workspace','profile-state']};
 const boundary={programFingerprint:contract.programFingerprint,supportsContract:value=>value===contract,
  async start({runtime,candidate,lease,claimChild}){lease.assertCurrent();events.push('module-start');runtime.configuration=candidate.effectiveConfiguration;
   runtime.child={syntheticModule:true};runtime.origin='http://127.0.0.1:43212';claimChild(runtime.child);
   return {...moduleHealthBinding(candidate,contract),child:runtime.child,origin:runtime.origin};},
  async verifyHealth({runtime,candidate,contract:chosen,binding}){events.push('module-health');assert.equal(chosen,contract);
   assert.deepEqual(binding,moduleHealthBinding(candidate,contract));assert.equal(runtime.configuration,candidate.effectiveConfiguration);return true;}};
 changeBoundary(boundary);
 const options={appId,getSelected:()=>selected,getGeneration:()=>generation,getRuntime:()=>runtime,authorize:data.options.authorize,
  canStage:()=>stageEligible&&Boolean(runtime.child)&&runtime.requestsAllowed!==false,onStatus:value=>states.push(value),
  createProvider:()=>{events.push('provider');return new GitHubModules(data.options);},
  setInterval:()=>({unref(){}}),clearInterval:()=>events.push('clear-timer'),
  ...(production?{}:{contract,boundary})};
 changeOptions(options);
 const startup=new ModuleDataStartup(options);
 t.after(async()=>{await startup.shutdown();data.cleanup();});
 return {data,runtime,startup,boundary,contract,events,states,get selected(){return selected;},set selected(value){selected=value;},
  get generation(){return generation;},set generation(value){generation=value;},set stageEligible(value){stageEligible=value;}};
}
module.exports={startupFixture};
