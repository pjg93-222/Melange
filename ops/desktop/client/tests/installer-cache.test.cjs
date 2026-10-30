'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {pruneInstallerCache}=require('../installer-cache.cjs');
function fixture(t,appId='melange'){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'installer-retention-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const updates=path.join(root,'updates'),baseline=path.join(root,'baseline');
  const put=(base,directory,name)=>{const file=path.join(base,directory,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,'non-installable fixture');return file;};
  return {root,updates,baseline,put,run:extra=>pruneInstallerCache({appId,currentVersion:'1.0.34',currentSequence:25,updatesRoots:[updates],baselineRoot:baseline,...extra})};
}
for(const app of ['melange','mentat','terrier'])test(app+': removes previous installers but keeps current, staged, recovery, and unrelated files',t=>{
  const f=fixture(t,app),packageFor=v=>`${app}-1.0.${v}-win32-x64.exe`;
  const old=f.put(f.updates,'24',packageFor(33)),ancient=f.put(f.updates,'20',packageFor(29));
  const baseline=f.put(f.baseline,'1.0.33',`${app} setup (2).exe`);
  const keep=[f.put(f.updates,'25',packageFor(34)),f.put(f.updates,'26',packageFor(35)),f.put(f.updates,'23',packageFor(32)),
    f.put(f.baseline,'1.0.34','current.exe'),f.put(f.baseline,'1.0.32','rollback.exe'),f.put(f.updates,'24','notes.txt'),
    f.put(f.updates,'24','other-app.exe'),f.put(f.updates,'24',packageFor(33)+'.part'),f.put(f.updates,'24/nested',packageFor(33)),
    f.put(f.updates,'not-a-sequence',packageFor(33)),f.put(f.root,'Downloads',packageFor(33))];
  assert.deepEqual(f.run({keepSequences:[23,26],keepVersions:['1.0.32','1.0.35']}).sort(),[old,ancient,baseline].sort());
  for(const file of keep)assert.ok(fs.existsSync(file),file);
  assert.deepEqual(f.run({keepSequences:[23,26],keepVersions:['1.0.32','1.0.35']}),[],'repeated cleanup is harmless');
});
test('cache cleanup refuses junctions at the root, ancestor, and version folder and skips hardlinks',t=>{
  const f=fixture(t),external=path.join(f.root,'external'),name='melange-1.0.33-win32-x64.exe';
  const file=f.put(external,'24',name),link=path.join(f.root,'linked');
  fs.symlinkSync(external,link,process.platform==='win32'?'junction':'dir');
  assert.deepEqual(f.run({updatesRoots:[link,path.join(link,'24')]}),[]);assert.ok(fs.existsSync(file));
  fs.mkdirSync(f.updates);fs.symlinkSync(path.join(external,'24'),path.join(f.updates,'24'),process.platform==='win32'?'junction':'dir');
  assert.deepEqual(f.run(),[]);assert.ok(fs.existsSync(file));
  fs.mkdirSync(path.join(f.updates,'23'));fs.linkSync(file,path.join(f.updates,'23',name));
  assert.deepEqual(f.run(),[]);assert.ok(fs.existsSync(file));
});
test('invalid release identity cannot trigger cleanup',t=>{
  const f=fixture(t),old=f.put(f.updates,'24','melange-1.0.33-win32-x64.exe');
  for(const extra of [{appId:'../melange'},{currentVersion:'../1.0.34'},{currentSequence:NaN},{currentSequence:0}])assert.deepEqual(f.run(extra),[]);
  assert.ok(fs.existsSync(old));
});
test('a manual upgrade also removes the previous native-cache installer, preserving staged recovery and unrelated downloads',t=>{
  const f=fixture(t),native=path.join(f.root,'native-cache');
  const old=f.put(native,'pending','melange-1.0.31-win32-x64.exe');
  const keep=[f.put(native,'pending','melange-1.0.34-win32-x64.exe'),f.put(native,'pending','melange-1.0.35-win32-x64.exe'),
    f.put(native,'pending','melange-1.0.33-win32-x64.exe'),f.put(native,'pending','mentat-1.0.31-win32-x64.exe'),f.put(native,'pending','update-info.json')];
  assert.deepEqual(f.run({nativeCacheDirectory:native,keepVersions:['1.0.33']}),[old]);
  for(const file of keep)assert.ok(fs.existsSync(file));
});
