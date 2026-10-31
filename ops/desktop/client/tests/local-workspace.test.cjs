'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),vm=require('node:vm');
const {hasLocalWorkspace}=require('../local-workspace.cjs');
function root(t){const p=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-local-workspace-'));t.after(()=>{assert.equal(path.dirname(path.resolve(p)),path.resolve(os.tmpdir()));assert.ok(path.basename(p).startsWith('desktop-local-workspace-'));fs.rmSync(p,{recursive:true,force:true});});return p;}
function seedWorkspace(appId,dataDirectory){
 fs.mkdirSync(dataDirectory,{recursive:true});
 if(appId==='melange'){fs.writeFileSync(path.join(dataDirectory,'Moneyball.html'),'x'.repeat(5000));fs.writeFileSync(path.join(dataDirectory,'ranks_python.json'),'{}');}
 else fs.mkdirSync(path.join(dataDirectory,'.cache','industry-report','empty-industry'),{recursive:true});
}

for(const appId of ['melange','mentat']){
 test(appId+' default data root never becomes an explicit workspace when files appear',t=>{
  const userData=root(t),dataDirectory=path.join(userData,'data');seedWorkspace(appId,dataDirectory);
  assert.equal(hasLocalWorkspace(appId,{dataDirectory}),true,'The pre-existing heuristic recognizes these files');
  assert.equal(hasLocalWorkspace(appId,{dataDirectory},{defaultDataDirectory:dataDirectory}),false);
  const external=path.join(userData,'selected-original');seedWorkspace(appId,external);
  assert.equal(hasLocalWorkspace(appId,{dataDirectory:external},{defaultDataDirectory:dataDirectory}),true);
 });

 test(appId+' actual main factory retains GitHub startup for default data and preserves an external workspace',t=>{
  const userData=root(t),dataDirectory=path.join(userData,'data');seedWorkspace(appId,dataDirectory);
  const original=path.join(userData,'selected-original');seedWorkspace(appId,original);
  const file=path.join(__dirname,'..','main.cjs'),source=fs.readFileSync(file,'utf8'),start=source.indexOf('function createModuleDataStartup()'),end=source.indexOf('\nfunction createWorkspaceDataStartup()',start);
  assert.ok(start>=0&&end>start);let configuration={dataDirectory},workspaceStarts=0;
  const startup={channel:'workspace-v1'},context={standaloneMode:true,definition:{id:appId},userData,path,
   applicationConfig:{desktopWorkspaceData:{[appId]:'workspace-v1'}},read:()=>configuration,
   createWorkspaceDataStartup:()=>{workspaceStarts++;return startup;},require:name=>{assert.equal(name,'./local-workspace.cjs');return require('../local-workspace.cjs');}};
  vm.runInNewContext(source.slice(start,end),context,{filename:file});
  assert.equal(context.createModuleDataStartup(),startup);assert.equal(workspaceStarts,1);
  configuration={dataDirectory:original};assert.equal(context.createModuleDataStartup(),null);assert.equal(workspaceStarts,1);
 });
}

test('a junction alias and Windows case variation of default data retain GitHub startup',t=>{
 const userData=root(t),defaultDataDirectory=path.join(userData,'data'),alias=path.join(userData,'data-alias');seedWorkspace('mentat',defaultDataDirectory);
 fs.symlinkSync(defaultDataDirectory,alias,process.platform==='win32'?'junction':'dir');
 assert.equal(hasLocalWorkspace('mentat',{dataDirectory:alias}),true);
 assert.equal(hasLocalWorkspace('mentat',{dataDirectory:alias},{defaultDataDirectory}),false);
 if(process.platform==='win32')assert.equal(hasLocalWorkspace('mentat',{dataDirectory:defaultDataDirectory.toUpperCase()},{defaultDataDirectory}),false);
});

for(const broken of ['selected','default'])test('unresolvable '+broken+' root retains GitHub startup',t=>{
 const userData=root(t),dataDirectory=path.join(userData,'selected-original'),defaultDataDirectory=path.join(userData,'data');seedWorkspace('mentat',dataDirectory);fs.mkdirSync(defaultDataDirectory);
 const native=fs.realpathSync.native,target=broken==='selected'?dataDirectory:defaultDataDirectory;
 t.mock.method(fs.realpathSync,'native',function(file,...args){if(file===target)throw new Error('Synthetic inaccessible path');return native.call(this,file,...args);});
 assert.equal(hasLocalWorkspace('mentat',{dataDirectory},{defaultDataDirectory}),false);
});
test('an existing Melange analytical workspace can use the legacy startup path',t=>{
 const dataDirectory=root(t);fs.writeFileSync(path.join(dataDirectory,'Moneyball.html'),'x'.repeat(5000));fs.writeFileSync(path.join(dataDirectory,'ranks_python.json'),'{}');
 assert.equal(hasLocalWorkspace('melange',{dataDirectory}),true);
 fs.unlinkSync(path.join(dataDirectory,'ranks_python.json'));assert.equal(hasLocalWorkspace('melange',{dataDirectory}),false);
});
test('empty, partially initialized and absent roots retain automatic first-use data setup',t=>{
 const dataDirectory=root(t);assert.equal(hasLocalWorkspace('melange',{dataDirectory}),false);assert.equal(hasLocalWorkspace('mentat',{dataDirectory}),false);
 fs.mkdirSync(path.join(dataDirectory,'state'));fs.writeFileSync(path.join(dataDirectory,'state','account'),'inert');assert.equal(hasLocalWorkspace('mentat',{dataDirectory}),false);
 assert.equal(hasLocalWorkspace('melange',{dataDirectory:path.join(dataDirectory,'missing')}),false);
});
test('existing Mentat caches or populated original inputs retain the local startup path',t=>{
 const dataDirectory=root(t);fs.mkdirSync(path.join(dataDirectory,'inputs'));fs.mkdirSync(path.join(dataDirectory,'config'));
 assert.equal(hasLocalWorkspace('mentat',{dataDirectory}),false);
 fs.writeFileSync(path.join(dataDirectory,'inputs','inert.json'),'{}');fs.writeFileSync(path.join(dataDirectory,'config','inert.json'),'{}');assert.equal(hasLocalWorkspace('mentat',{dataDirectory}),true);
 assert.equal(hasLocalWorkspace('mentat',{dataDirectory},{defaultDataDirectory:path.join(dataDirectory,'default-data')}),true);
});
test('reserved source descriptors and Terrier do not opt out of their native data boundaries',t=>{
 const dataDirectory=root(t);fs.writeFileSync(path.join(dataDirectory,'Moneyball.html'),'x'.repeat(5000));fs.writeFileSync(path.join(dataDirectory,'ranks_python.json'),'{}');
 for(const key of ['ownerGitHubModuleData','ownerGitHubWorkspaceData','ownerGitHubData'])assert.equal(hasLocalWorkspace('melange',{dataDirectory,[key]:{}}),false);
 assert.equal(hasLocalWorkspace('terrier',{dataDirectory}),false);assert.equal(hasLocalWorkspace('melange',{dataDirectory:'relative'}),false);
});
