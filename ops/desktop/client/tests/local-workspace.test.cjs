'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {hasLocalWorkspace}=require('../local-workspace.cjs');
function root(t){const p=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-local-workspace-'));t.after(()=>fs.rmSync(p,{recursive:true,force:true}));return p;}
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
});
test('reserved source descriptors and Terrier do not opt out of their native data boundaries',t=>{
 const dataDirectory=root(t);fs.writeFileSync(path.join(dataDirectory,'Moneyball.html'),'x'.repeat(5000));fs.writeFileSync(path.join(dataDirectory,'ranks_python.json'),'{}');
 for(const key of ['ownerGitHubModuleData','ownerGitHubWorkspaceData','ownerGitHubData'])assert.equal(hasLocalWorkspace('melange',{dataDirectory,[key]:{}}),false);
 assert.equal(hasLocalWorkspace('terrier',{dataDirectory}),false);assert.equal(hasLocalWorkspace('melange',{dataDirectory:'relative'}),false);
});
