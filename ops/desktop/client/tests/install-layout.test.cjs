'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const layout=require('../install-layout.cjs');
const {LAYOUT}=layout;
const D='C:\\U\\Downloads';

function tree(t){const base=fs.mkdtempSync(path.join(os.tmpdir(),'dl-'));t.after(()=>fs.rmSync(base,{recursive:true,force:true}));return base;}
function make(file,content='x'){fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,content);}
function program(directory,product){make(path.join(directory,product+'.exe'));make(path.join(directory,'resources','app.asar'));}

test('naming helpers build the Downloads layout from the config point',()=>{
  assert.equal(layout.fill('{product}-{version}',{product:'Melange',version:'1.0.19'}),'Melange-1.0.19');
  assert.equal(layout.root(D),D+'\\MelangeApplications');
  assert.equal(layout.appDirectory(D,'Melange','1.0.19'),D+'\\MelangeApplications\\Melange-1.0.19');
  assert.equal(layout.updaterCacheDirectory(D,'melange'),D+'\\MelangeApplications\\updates\\melange');
  assert.equal(layout.setupTempDirectory(D,'melange','1.0.19'),D+'\\MelangeApplications\\updates\\melange-setup');
  assert.equal(layout.updatesDirectory(D),D+'\\MelangeApplications\\updates');
  assert.equal(LAYOUT.keepVersions,2);assert.equal(LAYOUT.rollbackFloor,'1.0.19');
  assert.throws(()=>{LAYOUT.keepVersions=3;});
});

test('isUnder is case-insensitive, relative-based, and never a string-prefix match',()=>{
  assert.equal(layout.isUnder('C:\\U\\Downloads\\MelangeApplications\\Melange-1.0.19\\Melange.exe','C:\\U\\Downloads\\MelangeApplications'),true);
  assert.equal(layout.isUnder('c:\\u\\DOWNLOADS\\melangeapplications\\x','C:\\U\\Downloads\\MelangeApplications'),true);
  assert.equal(layout.isUnder('C:\\U\\Downloads\\MelangeApplications2\\x','C:\\U\\Downloads\\MelangeApplications'),false);
  assert.equal(layout.isUnder('C:\\U\\Downloads\\MelangeApplications','C:\\U\\Downloads\\MelangeApplications'),false);
  assert.equal(layout.isUnder('D:\\U\\Downloads\\MelangeApplications\\x','C:\\U\\Downloads\\MelangeApplications'),false);
});

test('downloadsMode is true only for an executable under the Downloads root',()=>{
  const exe=name=>D+'\\'+name;
  assert.equal(layout.downloadsMode({execPath:exe('MelangeApplications\\Melange-1.0.19\\Melange.exe'),downloads:D}),true);
  assert.equal(layout.downloadsMode({execPath:exe('MELANGEAPPLICATIONS\\Melange-1.0.19\\Melange.exe'),downloads:D}),true);
  for(const execPath of ['C:\\U\\Documents\\MelangeApplications\\Melange\\Melange.exe','C:\\U\\AppData\\Local\\Programs\\Melange\\Melange.exe',
    exe('MelangeApplications2\\Melange-1.0.19\\Melange.exe'),exe('Melange-1.0.19\\Melange.exe')])
    assert.equal(layout.downloadsMode({execPath,downloads:D}),false,execPath);
  assert.equal(layout.downloadsMode({execPath:exe('MelangeApplications\\x.exe'),downloads:null}),false);
});

test('fitsPath and deepestRelative implement the MAX_PATH budget',t=>{
  const max=LAYOUT.maxPath-LAYOUT.deepestRelativeBudget-1;
  assert.equal(layout.fitsPath('x'.repeat(max)),true);assert.equal(layout.fitsPath('x'.repeat(max+1)),false);
  assert.equal(max,108);
  const base=tree(t);make(path.join(base,'a','b','c.txt'));make(path.join(base,'short.txt'));
  assert.equal(layout.deepestRelative(base),'a\\b\\c.txt'.length);
  assert.equal(layout.deepestRelative(path.join(base,'missing')),0);
});

test('F2: the versionless setup folder keeps NSIS plugins under Downloads for user names up to 27 characters',()=>{
  // installer.nsh moves TEMP only when the setup path is <= DL_MAX_SETUP (88); the 1.0.19 name allowed 20 characters.
  const setup=user=>layout.setupTempDirectory('C:\\Users\\'+user+'\\Downloads','melange','1.0.19');
  for(const app of ['melange','terrier'])assert.equal(layout.setupTempDirectory(D,app,'9.99.999'),layout.setupTempDirectory(D,app,'1.0.19'),'no version in the name');
  assert.equal(layout.maxSetup(),88);
  assert.equal(setup('u'.repeat(27)).length<=layout.maxSetup(),true);assert.equal(setup('u'.repeat(28)).length<=layout.maxSetup(),false);
  assert.equal(('C:\\Users\\'+'u'.repeat(21)+'\\Downloads\\MelangeApplications\\updates\\'+layout.fill(LAYOUT.legacySetupFolder,{app:'melange',version:'1.0.19'})).length<=layout.maxSetup(),false,'the old name did not fit at 21');
});

test('nsisInclude carries every config value and includes the absolute installer.nsh',()=>{
  const text=layout.nsisInclude({product:'Melange',app:'melange',version:'1.0.19',installerNsh:'C:\\w\\ops\\desktop\\client\\installer.nsh'});
  for(const line of ['!define DL_ROOT_NAME "MelangeApplications"','!define DL_UPDATES_NAME "updates"','!define DL_APP_FOLDER "Melange-1.0.19"','!define DL_SETUP_FOLDER "melange-setup"',
    '!define DL_CACHE_FOLDER "melange"','!define DL_KNOWN_FOLDER "{374DE290-123F-4565-9164-39C4925E467B}"','!define DL_MAX_DIR 108','!define DL_MAX_SETUP 88',
    '!include "C:\\w\\ops\\desktop\\client\\installer.nsh"'])assert.ok(text.includes(line),line);
  assert.ok(text.indexOf('!define DL_MAX_SETUP')<text.indexOf('!include'),'defines come before the include');
  assert.match(layout.nsisInclude({product:'Terrier',app:'terrier',version:'1.0.20',installerNsh:'x'}),/DL_APP_FOLDER "Terrier-1\.0\.20"[\s\S]*DL_SETUP_FOLDER "terrier-setup"[\s\S]*DL_CACHE_FOLDER "terrier"/);
});

const FOLDERS=['Melange-1.0.17','Melange-1.0.18','Melange-1.0.19','Melange-1.0.20','Mentat-1.0.19','Terrier-1.0.19','Melange.bak-x','Melange-1.0.19-old','Melange-1.0.19.bak','melange-1.0.16'];
test('pruneTargets keeps the current version, protected versions and fills to the keep count',()=>{
  const base={entries:FOLDERS,product:'Melange',current:'1.0.20',keep:2};
  assert.deepEqual(layout.pruneTargets({...base,protect:[]}).sort(),['Melange-1.0.17','Melange-1.0.18']);
  assert.deepEqual(layout.pruneTargets({...base,protect:['1.0.18']}).sort(),['Melange-1.0.17','Melange-1.0.19']);
  assert.deepEqual(layout.pruneTargets({...base,protect:['1.0.18','1.0.17','1.0.19']}).sort(),[],'protection can exceed the keep count');
  for(const names of [layout.pruneTargets({...base,protect:[]}),layout.pruneTargets({...base,protect:['1.0.18']})])
    for(const name of names)assert.match(name,/^Melange-\d+\.\d+\.\d+$/,'only exact Melange-x.y.z folders are ever listed');
  assert.deepEqual(layout.pruneTargets({entries:['Melange-1.0.20'],product:'Melange',current:'1.0.20',keep:2}),[]);
  assert.deepEqual(layout.pruneTargets({entries:['Mentat-1.0.17','Mentat-1.0.18'],product:'Melange',current:'1.0.20',keep:2}),[]);
});

test('pruneTargets skips a junction or symlink when given the root',t=>{
  const root=tree(t),outside=tree(t);
  for(const name of ['Melange-1.0.17','Melange-1.0.18','Melange-1.0.20'])fs.mkdirSync(path.join(root,name));
  fs.symlinkSync(outside,path.join(root,'Melange-1.0.16'),'junction');
  const names=layout.pruneTargets({entries:fs.readdirSync(root),product:'Melange',current:'1.0.20',keep:2,protect:[],root,fs});
  assert.deepEqual(names.sort(),['Melange-1.0.17']);
  assert.ok(!names.includes('Melange-1.0.16'));
});

function state(t){
  const base=tree(t),downloads=path.join(base,'Downloads'),documents=path.join(base,'Documents'),home=base,localAppData=path.join(base,'AppData','Local');
  const root=path.join(downloads,'MelangeApplications');
  const execPath=path.join(root,'Melange-1.0.20','Melange.exe');
  fs.mkdirSync(path.dirname(execPath),{recursive:true});
  return {base,downloads,documents,home,localAppData,root,execPath,userData:path.join(documents,'MelangeApplicationState','melange'),
    args:{downloads,documents,home,localAppData,product:'Melange',app:'melange',applicationId:'org.melange.desktop.melange',current:'1.0.20',execPath,userData:path.join(documents,'MelangeApplicationState','melange'),state:{}}};
}

test('legacyCandidates lists exactly the three D-4 program folders, de-duplicated',()=>{
  const list=layout.legacyCandidates({product:'Melange',home:'C:\\Users\\p',documents:'C:\\Users\\p\\Documents',localAppData:'C:\\Users\\p\\AppData\\Local'});
  assert.deepEqual(list,['C:\\Users\\p\\Documents\\MelangeApplications\\Melange','C:\\Users\\p\\AppData\\Local\\Programs\\Melange']);
  const moved=layout.legacyCandidates({product:'Melange',home:'C:\\Users\\p',documents:'D:\\Docs',localAppData:'C:\\Users\\p\\AppData\\Local'});
  assert.equal(moved.length,3);assert.ok(moved.includes('D:\\Docs\\MelangeApplications\\Melange'));
});

test('legacy cleanup is a no-op outside Downloads mode (the Documents installation)',async t=>{
  const s=state(t),legacy=path.join(s.documents,'MelangeApplications','Melange');program(legacy,'Melange');
  const documentsExec=path.join(legacy,'Melange.exe');
  const result=await layout.sweepLayout({...s.args,execPath:documentsExec});
  assert.deepEqual(result,{pruned:[],setupRemoved:[],legacyRemoved:[]});
  assert.ok(fs.existsSync(documentsExec));
});

test('legacy cleanup removes only the exact program folder and leaves .bak siblings and state alone',async t=>{
  const s=state(t),legacy=path.join(s.documents,'MelangeApplications','Melange'),bak=path.join(s.documents,'MelangeApplications','Melange.bak-20261020'),stateDir=path.join(s.documents,'MelangeApplicationState','melange');
  program(legacy,'Melange');program(bak,'Melange');make(path.join(stateDir,'settings.json'));make(path.join(s.localAppData,'MelangeData','terrier','keep.txt'));
  const programs=path.join(s.localAppData,'Programs','Melange');program(programs,'Melange');
  const logs=[];
  const result=await layout.sweepLayout({...s.args,log:m=>logs.push(m)});
  assert.equal(fs.existsSync(legacy),false);assert.equal(fs.existsSync(programs),false);
  assert.equal(fs.existsSync(path.join(bak,'Melange.exe')),true,'.bak sibling intact');
  assert.equal(fs.existsSync(path.join(stateDir,'settings.json')),true,'MelangeApplicationState intact');
  assert.equal(fs.existsSync(path.join(s.localAppData,'MelangeData','terrier','keep.txt')),true);
  assert.equal(fs.existsSync(path.join(s.documents,'MelangeApplications')),true,'the parent is never removed');
  assert.deepEqual(result.legacyRemoved.sort(),[legacy,programs].sort());
  assert.ok(logs.some(line=>line.includes(legacy)));
});

test('legacy cleanup keeps a folder that is not a program folder, is a link, or is the running app',async t=>{
  const s=state(t);
  const noExe=path.join(s.documents,'MelangeApplications','Melange');make(path.join(noExe,'resources','app.asar'));
  await layout.sweepLayout(s.args);assert.equal(fs.existsSync(noExe),true,'missing Melange.exe');
  fs.rmSync(noExe,{recursive:true});
  const noAsar=path.join(s.localAppData,'Programs','Melange');make(path.join(noAsar,'Melange.exe'));
  await layout.sweepLayout(s.args);assert.equal(fs.existsSync(noAsar),true,'missing app.asar');
  fs.rmSync(noAsar,{recursive:true});
  // junction candidate
  const target=path.join(s.base,'elsewhere');program(target,'Melange');
  const parent=path.join(s.documents,'MelangeApplications');fs.mkdirSync(parent,{recursive:true});
  fs.symlinkSync(target,path.join(parent,'Melange'),'junction');
  await layout.sweepLayout(s.args);
  assert.equal(fs.existsSync(path.join(target,'Melange.exe')),true,'junction target untouched');assert.ok(fs.lstatSync(path.join(parent,'Melange')).isSymbolicLink());
  fs.unlinkSync(path.join(parent,'Melange'));
  // parent is a junction
  const realParent=path.join(s.base,'realparent');program(path.join(realParent,'Melange'),'Melange');
  fs.rmSync(parent,{recursive:true});fs.symlinkSync(realParent,parent,'junction');
  await layout.sweepLayout(s.args);assert.equal(fs.existsSync(path.join(realParent,'Melange','Melange.exe')),true,'linked parent');
  fs.unlinkSync(parent);
  // candidate equals the exec dir
  const same=path.join(s.documents,'MelangeApplications','Melange');program(same,'Melange');
  await layout.sweepLayout({...s.args,execPath:path.join(same,'Melange.exe')});assert.equal(fs.existsSync(path.join(same,'Melange.exe')),true);
});

test('legacy cleanup logs and leaves a busy folder, and never throws',async t=>{
  const s=state(t),legacy=path.join(s.documents,'MelangeApplications','Melange');program(legacy,'Melange');
  const real=fs.promises,logs=[];
  const stub={...fs,promises:new Proxy(real,{get:(target,key)=>key==='rm'?async p=>{if(String(p).toLowerCase()===legacy.toLowerCase()){const e=new Error('busy');e.code='EBUSY';throw e;}return target.rm(p,{recursive:true});}:target[key]})};
  const result=await layout.sweepLayout({...s.args,fs:stub,log:m=>logs.push(m)});
  assert.deepEqual(result.legacyRemoved,[]);assert.ok(logs.some(line=>/EBUSY|busy/.test(line)));assert.equal(fs.existsSync(legacy),true);
});

test('legacy cleanup refuses candidates that overlap protected paths',async t=>{
  const s=state(t);
  // userData inside the candidate (a profile nested in a program folder) must keep it
  const legacy=path.join(s.documents,'MelangeApplications','Melange');program(legacy,'Melange');
  await layout.sweepLayout({...s.args,userData:path.join(legacy,'profile')});
  assert.equal(fs.existsSync(path.join(legacy,'Melange.exe')),true);
  // a .bak segment anywhere in the path
  const bakHome=path.join(s.base,'x.BAK-1');const localAppData=path.join(bakHome,'AppData','Local');
  const programs=path.join(localAppData,'Programs','Melange');program(programs,'Melange');
  await layout.sweepLayout({...s.args,localAppData});assert.equal(fs.existsSync(path.join(programs,'Melange.exe')),true);
});

test('the keep-2 sweep deletes old version folders and stale setup folders, protecting pending, previous and recovery',async t=>{
  const s=state(t);
  for(const v of ['1.0.17','1.0.18','1.0.19','1.0.20'])program(path.join(s.root,'Melange-'+v),'Melange');
  program(path.join(s.root,'Mentat-1.0.17'),'Mentat');program(path.join(s.root,'Melange.bak-x'),'Melange');
  for(const name of ['melange-1.0.17-setup','melange-1.0.20-setup','melange-1.0.21-setup','melange-setup','melange-1.0.19-old','mentat-1.0.17-setup'])fs.mkdirSync(path.join(s.root,'updates',name),{recursive:true});
  make(path.join(s.root,'updates','melange','pending','melange-1.0.21-win32-x64.exe'));
  const result=await layout.sweepLayout({...s.args,state:{pending:{version:'1.0.21'},previous:{version:'1.0.18'},recovery:{phase:'prepared',target:{version:'1.0.17'}}}});
  const left=fs.readdirSync(s.root).sort();
  assert.deepEqual(left,['Melange-1.0.17','Melange-1.0.18','Melange-1.0.20','Melange.bak-x','Mentat-1.0.17','updates'].sort(),'1.0.19 is the only unprotected extra');
  // F2: the live folder is the versionless one; every 1.0.19-style versioned folder is a leftover (another app's is never touched)
  assert.deepEqual(fs.readdirSync(path.join(s.root,'updates')).sort(),['melange','melange-1.0.19-old','melange-setup','mentat-1.0.17-setup'],'only stale setup folders go; the cache stays');
  assert.deepEqual(result.pruned,[path.join(s.root,'Melange-1.0.19')]);
  assert.deepEqual(result.setupRemoved.sort(),['melange-1.0.17-setup','melange-1.0.20-setup','melange-1.0.21-setup'].map(name=>path.join(s.root,'updates',name)));
  // finished recovery no longer protects
  await layout.sweepLayout({...s.args,state:{previous:{version:'1.0.18'},recovery:{phase:'completed',target:{version:'1.0.17'}}}});
  assert.equal(fs.existsSync(path.join(s.root,'Melange-1.0.17')),false);assert.equal(fs.existsSync(path.join(s.root,'Melange-1.0.18')),true);
});

test('the sweep never deletes the running folder, a linked version folder, or anything outside the root',async t=>{
  const s=state(t),outside=path.join(s.base,'outside');program(outside,'Melange');
  program(path.join(s.root,'Melange-1.0.20'),'Melange');program(path.join(s.root,'Melange-1.0.19'),'Melange');
  fs.symlinkSync(outside,path.join(s.root,'Melange-1.0.10'),'junction');fs.symlinkSync(outside,path.join(s.root,'Melange-1.0.11'),'junction');
  // the running exec is in an old folder (a rollback): it must survive even though it is not "current"
  const rolled=path.join(s.root,'Melange-1.0.12');program(rolled,'Melange');
  await layout.sweepLayout({...s.args,current:'1.0.19',execPath:path.join(rolled,'Melange.exe')});
  assert.equal(fs.existsSync(path.join(rolled,'Melange.exe')),true);
  assert.equal(fs.existsSync(path.join(outside,'Melange.exe')),true,'junction target untouched');
});

test('an unreadable root or a sweep with nothing to do does not throw',async t=>{
  const s=state(t);fs.rmSync(s.root,{recursive:true});
  assert.deepEqual(await layout.sweepLayout({...s.args,execPath:path.join(s.root,'Melange-1.0.20','Melange.exe')}),{pruned:[],setupRemoved:[],legacyRemoved:[]});
});

test('downloadsWarnings: redirect, OneDrive, Storage Sense and policy, each naming the resolved path',()=>{
  const home='C:\\Users\\p',downloads=home+'\\Downloads',root=downloads+'\\MelangeApplications';
  assert.deepEqual(layout.downloadsWarnings({downloads,home,env:{},storagePolicy:{'01':1,'32':0,'512':0}}),[]);
  assert.deepEqual(layout.downloadsWarnings({downloads:downloads.toUpperCase(),home,env:{}}),[],'case-insensitive');
  const redirect=layout.downloadsWarnings({downloads:'E:\\Data\\Dl',home,env:{}});
  assert.deepEqual(redirect,['Downloads is redirected to E:\\Data\\Dl. Tell IT this path if the app is blocked.']);
  const cloud=layout.downloadsWarnings({downloads:'C:\\Users\\p\\OneDrive - Org\\Downloads',home,env:{OneDriveCommercial:'C:\\Users\\p\\OneDrive - Org'}});
  assert.equal(cloud.length,2);assert.ok(cloud.some(w=>w==='Downloads is inside OneDrive (C:\\Users\\p\\OneDrive - Org\\Downloads); files may be moved to the cloud or locked while syncing.'));
  for(const name of ['OneDrive','OneDriveConsumer'])assert.ok(layout.downloadsWarnings({downloads:'C:\\Users\\p\\OneDrive\\Downloads',home,env:{[name]:'C:\\Users\\p\\OneDrive'}}).some(w=>/inside OneDrive/.test(w)),name);
  const sense=layout.downloadsWarnings({downloads,home,env:{},storagePolicy:{'01':1,'32':1,'512':30}});
  assert.deepEqual(sense,['Storage Sense deletes Downloads files not opened for 30 days; this app lives in '+root+'.']);
  for(const off of [{'01':0,'32':1,'512':30},{'01':1,'32':0,'512':30},{'01':1,'32':1,'512':0},{}])assert.deepEqual(layout.downloadsWarnings({downloads,home,env:{},storagePolicy:off}),[]);
  assert.deepEqual(layout.downloadsWarnings({downloads,home,env:{},storagePolicy:{'01':'0x1','32':'0x1','512':'0x1e'}}).length,1,'registry hex strings are accepted');
  const policy=layout.downloadsWarnings({downloads,home,env:{},storagePolicyGpo:{ConfigStorageSenseDownloadsCleanupThreshold:14}});
  assert.deepEqual(policy,['Storage Sense deletes Downloads files not opened for 14 days (set by policy); this app lives in '+root+'.']);
  assert.deepEqual(layout.downloadsWarnings({downloads,home,env:{},storagePolicyGpo:{ConfigStorageSenseDownloadsCleanupThreshold:14,AllowStorageSenseGlobal:0}}),[]);
  assert.deepEqual(layout.downloadsWarnings({downloads,home,env:{},storagePolicyGpo:{ConfigStorageSenseDownloadsCleanupThreshold:0}}),[]);
});

test('parseRegQuery reads reg.exe output into a name/value map',()=>{
  const text='\r\nHKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\StorageSense\\Parameters\\StoragePolicy\r\n    01    REG_DWORD    0x1\r\n    32    REG_DWORD    0x1\r\n    512    REG_DWORD    0x1e\r\n\r\n';
  assert.deepEqual(layout.parseRegQuery(text),{'01':'0x1','32':'0x1','512':'0x1e'});
  assert.deepEqual(layout.parseRegQuery(''),{});
});

test('storage policy is read through reg.exe from System32 and tolerates failure',async t=>{
  const calls=[];
  const execFile=(file,args)=>{calls.push([file,args]);return Promise.resolve({stdout:'    01    REG_DWORD    0x1\r\n'});};
  const values=await layout.registryValues(execFile,'HKCU\\x',{SystemRoot:'C:\\Windows'});
  assert.deepEqual(values,{'01':'0x1'});assert.equal(calls[0][0],'C:\\Windows\\System32\\reg.exe');assert.deepEqual(calls[0][1],['query','HKCU\\x']);
  assert.deepEqual(await layout.registryValues(()=>Promise.reject(new Error('missing')),'HKCU\\x',{SystemRoot:'C:\\Windows'}),{});
});

test('the install-layout module is in the release file list',()=>{assert.ok(require('../release-files.cjs').includes('install-layout.cjs'));});

test('main.cjs wires the layout only for an app running from Downloads, and leaves the legacy updater call unchanged',()=>{
  const main=fs.readFileSync(path.join(__dirname,'..','main.cjs'),'utf8');
  assert.match(main,/documents:\(\)=>app\.getPath\('documents'\),downloads:\(\)=>app\.getPath\('downloads'\),protectedPaths:/);
  assert.match(main,/const downloadsFolder=process\.platform==='win32'&&app\.isPackaged&&!profile\.isolated\?app\.getPath\('downloads'\):null;/);
  assert.match(main,/const layoutMode=Boolean\(downloadsFolder&&dlLayout\.downloadsMode\(\{execPath:process\.execPath,downloads:downloadsFolder\}\)\);/);
  assert.match(main,/const installLayout=layoutMode\?\{cacheDirectory:dlLayout\.updaterCacheDirectory\(downloadsFolder,definition\.id\),\s*sweep:/);
  assert.ok(!/installDirectory:version/.test(main),'no /D from the app');
  assert.match(main,/if\(layoutMode\)dlLayout\.layoutWarnings\(/);
  assert.match(main,/new DesktopUpdater\(\{installLayout,\.\.\.githubOptions,/);
  assert.match(main,/autoUpdater:require\('electron-updater'\)\.autoUpdater,packaged:/);
  assert.match(main,/const dlLayout=require\('\.\/install-layout\.cjs'\);/);
});

test('F1: the sweep that runs before recover() keeps the version just updated from (installed), alongside previous and pending',async t=>{
  const s=state(t);
  for(const v of ['1.0.19','1.0.20','1.0.21'])program(path.join(s.root,'Melange-'+v),'Melange');
  const result=await layout.sweepLayout({...s.args,current:'1.0.21',execPath:path.join(s.root,'Melange-1.0.21','Melange.exe'),
    state:{installed:{version:'1.0.20'},previous:{version:'1.0.19'},pending:{version:'1.0.21'}}});
  assert.deepEqual(result.pruned,[]);
  assert.deepEqual(fs.readdirSync(s.root).sort(),['Melange-1.0.19','Melange-1.0.20','Melange-1.0.21']);
});

test('L3: nothing is pruned when the Downloads root itself is a junction',async t=>{
  const s=state(t),elsewhere=path.join(s.base,'elsewhere');
  for(const v of ['1.0.17','1.0.18','1.0.19'])program(path.join(elsewhere,'Melange-'+v),'Melange');
  fs.mkdirSync(path.join(elsewhere,'updates','melange-1.0.17-setup'),{recursive:true});
  fs.rmSync(s.root,{recursive:true});fs.symlinkSync(elsewhere,s.root,'junction');
  const result=await layout.sweepLayout({...s.args,execPath:path.join(s.root,'Melange-1.0.19','Melange.exe'),current:'1.0.19'});
  assert.deepEqual(result,{pruned:[],setupRemoved:[],legacyRemoved:[]});
  assert.equal(fs.readdirSync(elsewhere).length,4);
});

test('L2: the generated include carries the version the installer must match',()=>{
  assert.ok(layout.nsisInclude({product:'Melange',app:'melange',version:'1.0.19',installerNsh:'x'}).includes('!define DL_VERSION "1.0.19"'));
});
