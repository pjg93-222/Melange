'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawnSync}=require('node:child_process');

// Each app updates from its own public repository; the variable, when set, overrides it (2026-10-15 correction).
const EXPECTED={melange:'pjg93-222/melange',mentat:'pjg93-222/mentat',terrier:'pjg93-222/geo'};

test('workspace distribution is an explicit compiled Melange-only mode; Mentat ships the public-only 1.0.32 config; Terrier and unknown values cannot select it',()=>{
 const fixture=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-workspace-build-'));
 try{
  for(const appId of Object.keys(EXPECTED)){
   fs.mkdirSync(path.join(fixture,appId,'bootstrap'),{recursive:true});fs.mkdirSync(path.join(fixture,appId,'python','bin'),{recursive:true});
   fs.writeFileSync(path.join(fixture,appId,'bootstrap','desktop_backend.py'),'');fs.writeFileSync(path.join(fixture,appId,'python','python.exe'),'');fs.writeFileSync(path.join(fixture,appId,'python','bin','python3'),'');
   for(const mode of ['disabled','workspace-v1','renderer-path']){
    const child=spawnSync(process.execPath,['-e',"const config=require('./builder.cjs');process.stdout.write(JSON.stringify(config.extraMetadata.desktopAppConfig.desktopWorkspaceData))"],{cwd:path.resolve(__dirname,'..'),encoding:'utf8',windowsHide:true,env:{...process.env,DESKTOP_APP_ID:appId,DESKTOP_RUNTIME_ROOT:fixture,DESKTOP_ACCESS_TRUST:'',DESKTOP_WORKSPACE_DATA_MODE:mode}});
    if(mode==='renderer-path'){assert.notEqual(child.status,0);assert.match(child.stderr,/workspace/);}
    else{assert.equal(child.status,0,child.stderr);assert.deepEqual(JSON.parse(child.stdout),mode==='workspace-v1'&&appId==='melange'?{melange:'workspace-v1'}:{});
     if(appId==='mentat')assert.deepEqual(JSON.parse(child.stdout),{},'Mentat never carries a workspace channel in its asar config');}
   }
  }
 }finally{assert.equal(path.dirname(fixture),path.resolve(os.tmpdir()));assert.ok(path.basename(fixture).startsWith('desktop-workspace-build-'));fs.rmSync(fixture,{recursive:true,force:true});}
});

function updateSource(fixture,appId,repository){
  const env={...process.env,DESKTOP_APP_ID:appId,DESKTOP_RUNTIME_ROOT:fixture,DESKTOP_ACCESS_TRUST:''};
  delete env.DESKTOP_GITHUB_REPOSITORY;delete env.DESKTOP_UPDATE_PROVIDER;
  if(repository!==undefined)env.DESKTOP_GITHUB_REPOSITORY=repository;
  const child=spawnSync(process.execPath,['-e',
    "const c=require('./builder.cjs');process.stdout.write(JSON.stringify({source:c.extraMetadata.desktopAppConfig.desktopUpdateSource,accessMode:c.extraMetadata.desktopAppConfig.desktopAccessMode,uninstaller:c.extraMetadata.desktopAppConfig.desktopUninstaller,nsis:c.nsis,target:c.win.target}))"],
    {cwd:path.resolve(__dirname,'..'),encoding:'utf8',windowsHide:true,env});
  assert.equal(child.status,0,child.stderr);
  const result=JSON.parse(child.stdout);
  assert.equal(result.accessMode,'standalone','new builds use local access without remote administrator approval');
  assert.equal(result.uninstaller,false,appId+' native metadata disables the uninstaller');
  assert.equal(result.nsis,undefined,'the normal build must not restore legacy installer plug-ins');
  assert.deepEqual(result.target,['dir'],'the signed directory is completed by build-native.cjs');
  return result.source;
}

function signingConfig(fixture,publisher){
  const env={...process.env,DESKTOP_APP_ID:'melange',DESKTOP_RUNTIME_ROOT:fixture,DESKTOP_ACCESS_TRUST:''};
  delete env.WINDOWS_PUBLISHER_NAME;if(publisher!==undefined)env.WINDOWS_PUBLISHER_NAME=publisher;
  const child=spawnSync(process.execPath,['-e',
    "const c=require('./builder.cjs');process.stdout.write(JSON.stringify({pin:c.extraMetadata.desktopAppConfig.windowsPublisherName,win:c.win,force:c.forceCodeSigning??null}))"],
    {cwd:path.resolve(__dirname,'..'),encoding:'utf8',windowsHide:true,env});
  assert.equal(child.status,0,child.stderr);
  return JSON.parse(child.stdout);
}

test('an unset DESKTOP_GITHUB_REPOSITORY gives each app its own repository, and a set one still wins',()=>{
  const fixture=fs.mkdtempSync(path.join(os.tmpdir(),'melange-update-source-'));
  try{
    for(const app of Object.keys(EXPECTED)){
      fs.mkdirSync(path.join(fixture,app,'python'),{recursive:true});
      fs.mkdirSync(path.join(fixture,app,'bootstrap'),{recursive:true});
      fs.writeFileSync(path.join(fixture,app,'python',process.platform==='win32'?'python.exe':'bin-python-placeholder'),'');
      if(process.platform!=='win32'){
        fs.mkdirSync(path.join(fixture,app,'python','bin'),{recursive:true});
        fs.writeFileSync(path.join(fixture,app,'python','bin','python3'),'');
      }
      fs.writeFileSync(path.join(fixture,app,'bootstrap','desktop_backend.py'),'');
    }
    for(const [app,repository] of Object.entries(EXPECTED)){
      assert.deepEqual(updateSource(fixture,app),{provider:'github',repository},app);
    }
    assert.deepEqual(updateSource(fixture,'mentat','Example/Override'),{provider:'github',repository:'example/override'});
    const source=fs.readFileSync(path.join(__dirname,'..','builder.cjs'),'utf8');
    assert.ok(!source.includes('melange-platform'),'the combined repository is no longer a default');
    // Explicit directory staging can carry the public pin without signing material.
    // Production build-native.cjs refuses this unsigned configuration. Without a
    // pin the packaged updater remains fail-closed.
    const subject='CN=Melange Systems Desktop Release (self-signed)';
    assert.deepEqual(signingConfig(fixture,subject),{pin:subject,force:null,
      win:{target:['dir'],icon:path.join(path.resolve(__dirname,'..'),'icons','melange.ico'),signtoolOptions:{publisherName:subject},verifyUpdateCodeSignature:true}});
    const unpinned=signingConfig(fixture);
    assert.equal(unpinned.pin,null);assert.equal(unpinned.win.signtoolOptions,undefined);assert.equal(unpinned.win.verifyUpdateCodeSignature,true);
  }finally{
    // Only the exact random fixture directory created by this test can be removed.
    assert.equal(path.dirname(fixture),path.resolve(os.tmpdir()));
    assert.ok(path.basename(fixture).startsWith('melange-update-source-'));
    fs.rmSync(fixture,{recursive:true,force:true});
  }
});

test('normal directory builds have no legacy NSIS target or generated script configuration',()=>{
  const fixture=fs.mkdtempSync(path.join(os.tmpdir(),'melange-update-source-'));
  try{
    fs.mkdirSync(path.join(fixture,'melange','python'),{recursive:true});fs.mkdirSync(path.join(fixture,'melange','bootstrap'),{recursive:true});
    fs.writeFileSync(path.join(fixture,'melange','python',process.platform==='win32'?'python.exe':'bin-python-placeholder'),'');
    if(process.platform!=='win32'){fs.mkdirSync(path.join(fixture,'melange','python','bin'),{recursive:true});fs.writeFileSync(path.join(fixture,'melange','python','bin','python3'),'');}
    fs.writeFileSync(path.join(fixture,'melange','bootstrap','desktop_backend.py'),'');
    const config=distRoot=>{
      const env={...process.env,DESKTOP_APP_ID:'melange',DESKTOP_RUNTIME_ROOT:fixture,DESKTOP_ACCESS_TRUST:''};delete env.DESKTOP_DIST_ROOT;if(distRoot)env.DESKTOP_DIST_ROOT=distRoot;
      const child=spawnSync(process.execPath,['-e',"const c=require('./builder.cjs');process.stdout.write(JSON.stringify({nsis:c.nsis,output:c.directories.output}))"],{cwd:path.resolve(__dirname,'..'),encoding:'utf8',windowsHide:true,env});
      assert.equal(child.status,0,child.stderr);return JSON.parse(child.stdout);
    };
    const before=fs.readdirSync(fixture).length;
    const plain=config();
    assert.equal(plain.nsis,undefined);assert.equal(plain.output,'dist/melange');
    const dist=path.join(fixture,'out');
    const rooted=config(dist);
    assert.equal(rooted.output,path.join(dist,'melange'));assert.equal(rooted.nsis,undefined);
    assert.equal(fs.readdirSync(fixture).length,before,'builder.cjs writes no files; after-pack is the only writer');
  }finally{
    assert.equal(path.dirname(fixture),path.resolve(os.tmpdir()));assert.ok(path.basename(fixture).startsWith('melange-update-source-'));
    fs.rmSync(fixture,{recursive:true,force:true});
  }
});
