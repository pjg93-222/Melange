'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {argumentsFor,buildNative}=require('../build-native.cjs');

function fixture(t){
 const projectDir=fs.mkdtempSync(path.join(os.tmpdir(),'native-build-'));
 t.after(()=>{assert.equal(path.dirname(projectDir),path.resolve(os.tmpdir()));fs.rmSync(projectDir,{recursive:true,force:true});});
 const output=path.join(projectDir,'dist','terrier'),program=path.join(output,'win-unpacked');
 fs.mkdirSync(path.join(program,'resources'),{recursive:true});fs.writeFileSync(path.join(program,'resources','app-update.yml'),'{}');
 const env={},calls=[];
 const context={electronPlatformName:'win32',appOutDir:program,packager:{appInfo:{version:'1.0.23'}}};
 const config={forceCodeSigning:true,directories:{output},extraMetadata:{desktopAppConfig:{appId:'terrier',desktopUninstaller:false}},
  beforePack:async()=>{calls.push('prepare');env.ELECTRON_BUILDER_NSIS_DIR=path.join(projectDir,'nsis');},
  afterSign:async()=>calls.push('program-signed'),
  win:{target:['dir'],signtoolOptions:{sign:async()=>calls.push('installer-signed')}},
  artifactBuildCompleted:async({file})=>{calls.push('receipt');fs.writeFileSync(file+'.signatures.json',JSON.stringify({appId:'terrier',installer:file,installerFormat:'builtin-nsis-v1',desktopUninstaller:false,installerPlugins:[]}));}};
 const api={Platform:{WINDOWS:'windows',MAC:'mac',LINUX:'linux'},createTargets:(platforms,type,arch)=>({platforms,type,arch}),
  build:async options=>{calls.push('electron-builder');assert.equal(options.publish,'never');assert.deepEqual(options.targets,{platforms:['windows'],type:'dir',arch:'x64'});await options.config.beforePack(context);await options.config.afterSign(context);return [];}};
 const compile=async request=>{calls.push('compile');assert.equal(request.compression,'zlib');assert.equal(request.makensis,env.ELECTRON_BUILDER_NSIS_DIR);assert.equal(request.program,program);fs.writeFileSync(request.output,'installer');return {installer:request.output,format:'builtin-nsis-v1'};};
 const options={env,platform:'win32',arch:'arm64',projectDir,electronBuilder:api,loadConfig:()=>config,compile};
 return {projectDir,output,program,env,calls,config,api,options};
}

test('normal Windows build keeps signing hooks in one process and publishes only a completed installer receipt',async t=>{
 const f=fixture(t),result=await buildNative(['--win','--x64','--publish','never'],f.options);
 assert.deepEqual(f.calls,['electron-builder','prepare','program-signed','compile','installer-signed','receipt']);
 assert.deepEqual(result,[path.join(f.output,'Terrier-1.0.23-win-x64.exe')]);
});

test('Windows production refuses unsigned config and legacy NSIS config before building',async t=>{
 const f=fixture(t);delete f.config.forceCodeSigning;
 await assert.rejects(buildNative(['--win'],f.options),/no unsigned fallback/);assert.deepEqual(f.calls,[]);
 f.config.forceCodeSigning=true;f.config.win.target=['nsis'];
 await assert.rejects(buildNative(['--win'],f.options),/built-in no-uninstaller/);assert.deepEqual(f.calls,[]);
});

test('Windows production refuses public upload without the signed-feed publisher',async t=>{
 const f=fixture(t);await assert.rejects(buildNative(['--win','--publish','always'],f.options),/signed-feed release pipeline/);assert.deepEqual(f.calls,[]);
});

test('compiler and signing failures cannot produce a final successful installer result',async t=>{
 const f=fixture(t);f.options.compile=async()=>{throw new Error('compiler failed');};
 await assert.rejects(buildNative(['--win'],f.options),/compiler failed/);assert.ok(!f.calls.includes('installer-signed'));
 const g=fixture(t);g.config.win.signtoolOptions.sign=async()=>{throw new Error('signing failed');};
 await assert.rejects(buildNative(['--win'],g.options),/signing failed/);assert.ok(!g.calls.includes('receipt'));
});

test('a missing signed-program callback or incorrect receipt fails closed',async t=>{
 const f=fixture(t);f.api.build=async()=>[];
 await assert.rejects(buildNative(['--win'],f.options),/signing phase did not complete/);assert.deepEqual(f.calls,[]);
 const g=fixture(t);g.config.artifactBuildCompleted=async({file})=>fs.writeFileSync(file+'.signatures.json','{}');
 await assert.rejects(buildNative(['--win'],g.options),/receipt is missing or mismatched/);
});

test('non-Windows builds retain their configured targets and do not invoke Windows compiler or signer',async()=>{
 const seen=[],config={mac:{target:['dmg','zip']}};
 const api={Platform:{MAC:'mac'},createTargets:(platforms,type,arch)=>({platforms,type,arch}),build:async options=>{seen.push(options);return ['App.dmg','App.zip'];}};
 const result=await buildNative(['--mac','--arm64','--publish=never'],{platform:'darwin',projectDir:__dirname,electronBuilder:api,loadConfig:()=>config,compile:()=>assert.fail('Windows compiler started')});
 assert.deepEqual(result,['App.dmg','App.zip']);assert.equal(seen[0].config,config);assert.deepEqual(seen[0].targets,{platforms:['mac'],type:null,arch:'arm64'});
});

test('explicit signed directory staging does not compile a Windows installer',async t=>{
 const f=fixture(t);assert.deepEqual(await buildNative(['--win','--dir'],f.options),[]);
 assert.deepEqual(f.calls,['electron-builder','prepare','program-signed']);
});

test('build arguments reject ambiguous platforms architectures and unknown switches',()=>{
 assert.deepEqual(argumentsFor([],{platform:'win32',arch:'arm64'}),{platform:'win32',arch:'x64',publish:'never',directoryOnly:false});
 for(const args of [['--win','--mac'],['--x64','--arm64'],['--publish'],['--config','other.cjs']])assert.throws(()=>argumentsFor(args));
});
