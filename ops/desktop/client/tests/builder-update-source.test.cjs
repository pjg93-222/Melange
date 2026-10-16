'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawnSync}=require('node:child_process');

// Each app updates from its own public repository; the variable, when set, overrides it (2026-10-15 correction).
const EXPECTED={melange:'pjg93-222/melange',mentat:'pjg93-222/mentat',terrier:'pjg93-222/geo'};

function updateSource(fixture,appId,repository){
  const env={...process.env,DESKTOP_APP_ID:appId,DESKTOP_RUNTIME_ROOT:fixture,DESKTOP_ACCESS_TRUST:''};
  delete env.DESKTOP_GITHUB_REPOSITORY;delete env.DESKTOP_UPDATE_PROVIDER;
  if(repository!==undefined)env.DESKTOP_GITHUB_REPOSITORY=repository;
  const child=spawnSync(process.execPath,['-e',
    "process.stdout.write(JSON.stringify(require('./builder.cjs').extraMetadata.desktopAppConfig.desktopUpdateSource))"],
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
  }finally{
    // Only the exact random fixture directory created by this test can be removed.
    assert.equal(path.dirname(fixture),path.resolve(os.tmpdir()));
    assert.ok(path.basename(fixture).startsWith('melange-update-source-'));
    fs.rmSync(fixture,{recursive:true,force:true});
  }
});
