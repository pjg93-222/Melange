'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const afterPack=require('../after-pack.cjs');

function pack(t,files){
  const appOutDir=fs.mkdtempSync(path.join(os.tmpdir(),'after-pack-'));t.after(()=>fs.rmSync(appOutDir,{recursive:true,force:true}));
  for(const relative of files){const target=path.join(appOutDir,'resources','runtime',...relative.split('/'));fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,'x');}
  return {appOutDir,exists:relative=>fs.existsSync(path.join(appOutDir,'resources','runtime',...relative.split('/')))};
}
const quiet=async(context)=>{const original=console.log,lines=[];console.log=line=>lines.push(line);try{await afterPack(context);}finally{console.log=original;}return lines;};

const THIRD_PARTY=['mentat/python/Lib/site-packages/pyproj/proj_dir/share/proj/proj.db','mentat/python/Lib/site-packages/pyogrio/proj_data/proj.db','mentat/native/R/doc/KEYWORDS.db',
  'mentat/native/R/share/licenses/license.db','mentat/native/R/library/RSQLite/db/datasets.sqlite','mentat/python/lib/x.sqlite3','mentat/python/state/readme.txt'];

test('state directories and databases under runtime/<app>/sources are removed and logged, and the build continues',async t=>{
  const planted=['mentat/sources/mentat/state/prewarm/access.sqlite','mentat/sources/mentat/state/prewarm/access.sqlite-wal','mentat/sources/mentat/state/prewarm/access.sqlite-shm',
    'mentat/sources/x/app/foo.db','mentat/sources/app/Cache/A.DB-WAL','mentat/sources/a/b/c/STATE/x.txt','terrier/Sources/app/d.sqlite3','mentat/sources/app/j.sqlite-journal'];
  const keep=['mentat/sources/app/server.py','mentat/sources/app/statement.txt',...THIRD_PARTY];
  const context=pack(t,[...planted,...keep]);
  const lines=await quiet(context);
  for(const file of planted)assert.equal(context.exists(file),false,file);
  assert.equal(context.exists('mentat/sources/mentat/state'),false,'the whole state directory is gone');
  for(const file of keep)assert.equal(context.exists(file),true,file+' must survive');
  assert.ok(lines.some(line=>/removed .*mentat.state$/.test(line))&&lines.some(line=>/removed .*foo\.db$/.test(line)),'each removed path is logged');
  assert.ok(lines.some(line=>/packing report: removed \d+ state\/database path/.test(line)));
});

test('a runtime without sources, or without a runtime at all, packs cleanly',async t=>{
  const context=pack(t,[...THIRD_PARTY]);await quiet(context);for(const file of THIRD_PARTY)assert.equal(context.exists(file),true,file);
  await quiet({appOutDir:path.join(context.appOutDir,'nowhere')});
});

test('builder wires the strip step as afterPack and keeps its glob filter inside sources',()=>{
  const source=fs.readFileSync(path.join(__dirname,'..','builder.cjs'),'utf8');
  assert.match(source,/afterPack:path\.join\(__dirname,'after-pack\.cjs'\)/);
  assert.ok(source.includes("'!sources/**/state/**'")&&source.includes("'!sources/**/*.{"),'filter patterns stay under sources/');
  assert.ok(!require('../release-files.cjs').includes('after-pack.cjs'),'build-time only, not shipped in the app');
});

test('an unreadable directory under sources is logged and skipped by stripState, then fails the N20 guard (fail closed)',async t=>{
  const context=pack(t,['mentat/sources/locked/a.sqlite','mentat/sources/app/b.db']);
  const locked=path.join(context.appOutDir,'resources','runtime','mentat','sources','locked'),read=fs.readdirSync;
  fs.readdirSync=(directory,...rest)=>{if(path.resolve(String(directory))===locked)throw Object.assign(new Error('EACCES: permission denied'),{code:'EACCES'});return read.call(fs,directory,...rest);};
  const lines=[];let failure;
  try{afterPack.stripState(path.join(context.appOutDir,'resources','runtime'),line=>lines.push(line));
    await quiet(context).catch(error=>{failure=error;});}finally{fs.readdirSync=read;}
  assert.equal(context.exists('mentat/sources/app/b.db'),false,'the readable branch is still stripped');
  assert.ok(lines.some(line=>/could not read .*locked: EACCES/.test(line)),'the unreadable directory is logged');
  assert.match(failure?.message??'',/EACCES/,'the N20 guard does not pass a directory it cannot read');
});

// ---- Downloads layout (DL-spec 1.3, 2.8): generated NSIS include and the build-time long-path gate ----
const layout=require('../install-layout.cjs');
function build(t,appId='terrier',version='1.0.19'){
  const output=fs.mkdtempSync(path.join(os.tmpdir(),'after-pack-out-'));t.after(()=>fs.rmSync(output,{recursive:true,force:true}));
  const appOutDir=path.join(output,'win-unpacked');fs.mkdirSync(appOutDir);fs.writeFileSync(path.join(appOutDir,'Terrier.exe'),'x');
  return {output,appOutDir,packager:{appInfo:{version},config:{extraMetadata:{desktopAppConfig:{appId}}}}};
}

test('afterPack writes installer.generated.nsh next to win-unpacked with this build\'s names and the absolute installer.nsh',async t=>{
  const context=build(t);await quiet(context);
  const text=fs.readFileSync(path.join(context.output,'installer.generated.nsh'),'utf8');
  assert.equal(text,layout.nsisInclude({product:'Terrier',app:'terrier',version:'1.0.19',installerNsh:path.join(__dirname,'..','installer.nsh')}));
  assert.match(text,/DL_APP_FOLDER "Terrier-1\.0\.19"/);assert.match(text,/DL_CACHE_FOLDER "terrier"/);assert.match(text,/!include "[A-Za-z]:\\[^"]*installer\.nsh"/);
  assert.ok(fs.existsSync(path.resolve(text.match(/!include "(.*)"/)[1])),'the included installer.nsh exists');
});

test('afterPack fails the build when the deepest packaged path exceeds the budget, and passes at the limit',async t=>{
  const budget=layout.LAYOUT.deepestRelativeBudget;
  const ok=build(t);const atLimit=path.join(ok.appOutDir,'d'.repeat(budget-'\f'.length));fs.writeFileSync(atLimit,'x');
  // a file whose relative path is exactly the budget
  const exact=path.join(ok.appOutDir,'e'.repeat(budget));fs.writeFileSync(exact,'x');
  await quiet(ok);
  const bad=build(t);fs.writeFileSync(path.join(bad.appOutDir,'e'.repeat(budget+1)),'x');
  await assert.rejects(()=>quiet(bad),/deepest packaged path is \d+ characters.*limit of 150/);
  assert.equal(fs.existsSync(path.join(bad.output,'installer.generated.nsh')),false,'nothing is generated for a build that fails the gate');
  // removed state paths do not count toward depth
  const stripped=build(t);const deep=path.join(stripped.appOutDir,'resources','runtime','mentat','sources','state',...Array(30).fill('long-directory-name'));fs.mkdirSync(deep,{recursive:true});fs.writeFileSync(path.join(deep,'f'),'x');
  await quiet(stripped);
});

test('afterPack without packager metadata (unit use) leaves no include behind',async t=>{
  const context=build(t);await quiet({appOutDir:context.appOutDir});assert.equal(fs.existsSync(path.join(context.output,'installer.generated.nsh')),false);
});

test('native no-uninstaller metadata generates the pinned custom script for this build',async t=>{
  const context=build(t,'melange','1.0.21');context.packager.config.extraMetadata.desktopAppConfig.desktopUninstaller=false;
  await quiet(context);
  assert.ok(fs.existsSync(path.join(context.output,'installer.no-uninstaller.nsi')));
  const evidence=JSON.parse(fs.readFileSync(path.join(context.output,'nsis-no-uninstaller.provenance.json'),'utf8'));
  assert.equal(evidence.mode,'native-without-uninstaller');assert.equal(evidence.electronBuilderVersion,'26.15.3');
});

test('built-in directory packaging writes the native updater pin without generating legacy NSIS files',async t=>{
  const context=build(t,'mentat','1.0.23');context.electronPlatformName='win32';
  const publisher='CN=Melange Systems Desktop Release (self-signed)';
  context.packager.config.win={target:['dir']};
  context.packager.config.publish={provider:'generic',url:'https://127.0.0.1/desktop-feed-disabled-until-paired/'};
  Object.assign(context.packager.config.extraMetadata.desktopAppConfig,{desktopUninstaller:false,windowsPublisherName:publisher});
  await quiet(context);
  const config=require('js-yaml').load(fs.readFileSync(path.join(context.appOutDir,'resources','app-update.yml'),'utf8'));
  assert.deepEqual(config,{provider:'generic',url:context.packager.config.publish.url,updaterCacheDirName:'mentat-desktop-updater',publisherName:[publisher]});
  for(const file of ['installer.generated.nsh','installer.no-uninstaller.nsi','nsis-no-uninstaller.provenance.json'])assert.equal(fs.existsSync(path.join(context.output,file)),false);
});

test('non-Windows packaging does not generate NSIS installer inputs',async t=>{
  const context=build(t);context.electronPlatformName='darwin';await quiet(context);
  assert.equal(fs.existsSync(path.join(context.output,'installer.generated.nsh')),false);
});

// ---- N20: the public installer ships a no-data dashboard shell only ----
test('N20: afterPack fails on a real Moneyball.html or a Melange dataset, and passes on the shell-only runtime',async t=>{
  const shell=['melange/sources/fec/surfaces/staffer_live_server.py','melange/bootstrap/melange_bootstrap.py','terrier/sources/data/field_dictionary.csv'];
  const ok=pack(t,shell);await quiet({appOutDir:ok.appOutDir});
  for(const bad of ['melange/Moneyball.html','terrier/moneyball.html','melange/sources/Moneyball.html','melange/sources/fec/MONEYBALL_Redesign.html','mentat/sources/app/moneyball.html','melange/sources/fec/data/members.xlsx','melange/sources/fec/data/votes.ndjson']){
    const context=pack(t,[...shell,bad]);
    await assert.rejects(()=>quiet({appOutDir:context.appOutDir}),/no-data dashboard shell \(N20\)/,bad);
  }
  assert.ok(afterPack.findShippedData(path.join(ok.appOutDir,'resources','runtime')).length===0);
});
