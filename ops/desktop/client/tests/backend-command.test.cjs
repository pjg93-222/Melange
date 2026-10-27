'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {backendCommand}=require('../backend-command.cjs');
test('native launcher uses only the selected app bundled interpreter and never host Python',t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-command-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  assert.throws(()=>backendCommand(root,'terrier','win32'),/runtime is not installed/);
  assert.throws(()=>backendCommand(root,'../terrier','win32'),/Unknown application/);
  const runtime=path.join(root,'runtime','terrier');fs.mkdirSync(path.join(runtime,'python'),{recursive:true});fs.mkdirSync(path.join(runtime,'bootstrap'));
  fs.writeFileSync(path.join(runtime,'python','python.exe'),'fixture');
  assert.throws(()=>backendCommand(root,'terrier','win32'),/runtime is not installed/);
  fs.writeFileSync(path.join(runtime,'bootstrap','desktop_backend.py'),'fixture');
  const command=backendCommand(root,'terrier','win32');assert.equal(command.binary,path.join(runtime,'python','python.exe'));assert.deepEqual(command.args,['-E','-B','-s','-u',path.join(runtime,'bootstrap','desktop_backend.py')]);
  assert.throws(()=>backendCommand(root,'mentat','win32'),/runtime is not installed/);
});


test('ordinary backend environment cannot inherit a module input authority or Python injection',()=>{
 const {backendEnvironment}=require('../backend-command.cjs'),keys=['DESKTOP_MODULE_INPUT','DESKTOP_MODULE_CONTRACT','PYTHONPATH'],before=Object.fromEntries(keys.map(key=>[key,process.env[key]]));
 try{for(const key of keys)process.env[key]='untrusted';const result=backendEnvironment();for(const key of keys)assert.equal(Object.hasOwn(result,key),false);assert.equal(result.PYTHONNOUSERSITE,'1');}
 finally{for(const key of keys)if(before[key]===undefined)delete process.env[key];else process.env[key]=before[key];}
});

test('backend and inherited Python helpers import without changing packaged program files',t=>{
 const {spawnSync}=require('node:child_process'),{backendEnvironment}=require('../backend-command.cjs');
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-bytecode-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const runtime=path.join(root,'runtime','melange'),bootstrap=path.join(runtime,'bootstrap');
 fs.mkdirSync(path.join(runtime,'python'),{recursive:true});fs.mkdirSync(bootstrap);
 fs.writeFileSync(path.join(runtime,'python','python.exe'),'fixture command selection');
 fs.writeFileSync(path.join(bootstrap,'program_module.py'),'VALUE = 42\n');
 fs.writeFileSync(path.join(bootstrap,'desktop_backend.py'),'import program_module,subprocess,sys\nassert program_module.VALUE == 42\nsubprocess.run([sys.executable,"-s","-c","import program_module"],check=True)\n');
 const command=backendCommand(root,'melange','win32');
 const result=spawnSync('python',command.args,{cwd:bootstrap,env:backendEnvironment(),encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);assert.equal(fs.existsSync(path.join(bootstrap,'__pycache__')),false);
});
