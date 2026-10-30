'use strict';
// Explicit integration runner: real packaged CPython/bootstrap and actual
// compiled public/workspace adapters. No verifier, child or response mocks.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');
const [programArg,publicArg,workspaceArg,reportArg]=process.argv.slice(2);
const need=(v,m)=>{if(!v)throw new Error(m);},read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
need([programArg,publicArg,workspaceArg,reportArg].every(p=>p&&path.isAbsolute(p)),'Arguments: actual-packaged-app public-request workspace-request output-report (absolute paths)');
const program=path.resolve(programArg),resources=path.join(program,'resources'),publicRequest=read(publicArg),workspaceRequest=read(workspaceArg),appId=publicRequest.appId;
need(['melange','mentat'].includes(appId)&&workspaceRequest.appId===appId,'Matching supported application required');
const {Runtime}=require('../../runtime.cjs'),contracts=require('../../module-data-startup.cjs'),{backendCommand,backendEnvironment}=require('../../backend-command.cjs');
const runtime=new Runtime(appId,path.dirname(reportArg),resources,{allowStandalone:true,authentication:'windows'}),context={runtime,resources};
const publicContract=contracts.compiledApplicationContract(appId,context),workspaceContract=contracts.withCompiledWorkspaceApplicationContract(appId,context,c=>c);
need(publicContract&&workspaceContract&&publicContract.programFingerprint===workspaceContract.programFingerprint,'Actual installed programme must support both compiled contracts');
function sha(p){return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');}
function input(request,contract){const adapter=contract.registry[request.kind];need(adapter,'Request must select the actual compiled channel kind');request.sourceRoot=path.join(resources,'runtime',appId,'sources');return {adapter,value:{dataset:{kind:request.kind,adapterVersion:1,objects:request.objects,counts:{files:request.objects.length}},root:request.snapshotRoot,files:request.files}};}
async function main(){
 const results=[];
 for(const [channel,request,contract] of [['public',publicRequest,publicContract],['workspace',workspaceRequest,workspaceContract]]){
  const {adapter,value}=input(request,contract),before=JSON.stringify(value),session=await adapter.prepareSnapshot({});
  try{need(await session.validateSnapshot(value)===true,'Real packaged CLI refused '+channel+' data');}finally{await session.cancel();}
  need(JSON.stringify(value)===before,'Read-only adapter changed caller data');
  results.push({channel,kind:request.kind,actualNativeResult:true,mode:'--desktop-github-module-check'});
 }
 const command=backendCommand(resources,appId),unknown=spawnSync(command.binary,[...command.args,'--desktop-unknown-module-check'],{env:backendEnvironment(),input:JSON.stringify(publicRequest),encoding:'utf8',timeout:15000,maxBuffer:1024**2,windowsHide:true});
 need(!unknown.error&&Number.isInteger(unknown.status)&&unknown.status!==0,'Unknown actual packaged CLI flag must fail closed');
 const result={schemaVersion:1,status:'passed-real-packaged-public-workspace-cli',appId,results,unknownFlagExit:unknown.status,programFingerprint:publicContract.programFingerprint,packagedInterpreter:{path:command.binary,sha256:sha(command.binary)},packagedBootstrap:{path:command.args.at(-1),sha256:sha(command.args.at(-1))},sourceAdapterSha256:sha(path.resolve(__dirname,'../../module-data-startup.cjs')),runnerSha256:sha(__filename),publicRequestSha256:sha(publicArg),workspaceRequestSha256:sha(workspaceArg),scope:'Actual readonly packaged CPython CLI through real compiled source adapters. No application launch, source-admission or native authorization claim; final rebuilt package still requires production native flow.'};
 fs.writeFileSync(reportArg,JSON.stringify(result,null,2)+'\n',{flag:'wx'});process.stdout.write(JSON.stringify(result)+'\n');
}
main().catch(error=>{process.stderr.write(String(error.stack)+'\n');process.exitCode=1;});
