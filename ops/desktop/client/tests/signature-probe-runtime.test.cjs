'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {verifyProbeRuntime}=require('../signature-probe-runtime.cjs');
const {verifyWindowsPackage}=require('../native-signature.cjs');
const {PIN}=require('./fixtures/native-signature-verdict.cjs');
const source=process.env.SIGNATURE_TEST_PYTHON_ROOT,signed=process.env.SIGNATURE_TEST_SIGNED_PE;
const enabled=process.platform==='win32'&&source&&signed;
test('authenticated isolated native probe rejects interpreter, bytecode and source changes',
 {skip:enabled?false:'Set SIGNATURE_TEST_PYTHON_ROOT and SIGNATURE_TEST_SIGNED_PE for real Windows probe'},async t=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'authenticated-signature-probe-'));
 t.after(()=>fs.rmSync(temporary,{recursive:true,force:true}));
 const resources=path.join(temporary,'resources'),runtime=path.join(resources,'runtime','mentat'),python=path.join(runtime,'python'),bootstrap=path.join(runtime,'bootstrap');
 for(const row of require('../signature-probe-runtime.json').applications.mentat){const to=path.join(python,...row.path.split('/'));fs.mkdirSync(path.dirname(to),{recursive:true});fs.copyFileSync(path.join(source,...row.path.split('/')),to);}
 fs.mkdirSync(bootstrap,{recursive:true});
 for(const name of ['desktop_backend.py','native_windows_signature.py'])fs.copyFileSync(path.resolve(__dirname,'../../packaging',name),path.join(bootstrap,name));
 const command=verifyProbeRuntime(resources,'mentat');assert.equal(command.binary,path.join(python,'python.exe'));
 assert.equal(verifyProbeRuntime(resources.toLowerCase(),'mentat').binary.toLowerCase(),command.binary.toLowerCase());
 assert.deepEqual(command.args.slice(0,4),['-I','-S','-B','-u']);
 await verifyWindowsPackage(signed,[PIN],{resources,appId:'mentat'});
 const {spawn}=require('node:child_process'),{once}=require('node:events'),activation=require('../installer-activation.cjs');
 const attempt=activation.createAttempt({appId:'mentat',version:'1.0.42',installerPath:command.binary,target:temporary});
 const child=spawn(command.binary,['-I','-S','-B','-c','import time; time.sleep(30)','--desktop-activation='+attempt.token],{windowsHide:true,stdio:'ignore'});
 try{
  await once(child,'spawn');const observed=await activation.inspectProcesses(attempt,{resources,appId:'mentat'});
  assert.equal(observed.length,1);assert.equal(observed[0].pid,child.pid);
  assert.ok(Date.parse(observed[0].startedAt)>=Date.parse(attempt.startedAt));
  assert.equal(Object.hasOwn(observed[0],'commandLine'),false);
  assert.deepEqual(await activation.inspectProcesses({...attempt,token:'0'.repeat(64)},{resources,appId:'mentat'}),[]);
 }finally{const exited=once(child,'exit');child.kill();await exited;}
 verifyProbeRuntime(resources,'mentat'); // The actual launch wrote no new bytecode.
 for(const filename of [path.join(python,'python.exe'),path.join(bootstrap,'native_windows_signature.py')]){
  const original=fs.readFileSync(filename),changed=Buffer.from(original);changed[changed.length-1]^=1;fs.writeFileSync(filename,changed);
  assert.throws(()=>verifyProbeRuntime(resources,'mentat'),/could not be authenticated/);fs.writeFileSync(filename,original);
 }
 for(const relative of ['Lib/injected.py','Lib/encodings/__pycache__/injected.cpython-312.pyc','python312._pth','pyvenv.cfg']){
  const filename=path.join(python,...relative.split('/')),parent=path.dirname(filename),created=!fs.existsSync(parent);
  fs.mkdirSync(parent,{recursive:true});fs.writeFileSync(filename,'unexpected import input');
  assert.throws(()=>verifyProbeRuntime(resources,'mentat'),/could not be authenticated/);fs.unlinkSync(filename);if(created)fs.rmdirSync(parent);
 }
 verifyProbeRuntime(resources,'mentat');
});
test('backend children cannot inherit Python path or venv launcher injection and disable bytecode writes',()=>{
 const before=process.env.__PYVENV_LAUNCHER__;process.env.__PYVENV_LAUNCHER__='untrusted';
 try{const env=require('../backend-command.cjs').backendEnvironment();assert.equal(env.__PYVENV_LAUNCHER__,undefined);assert.equal(env.PYTHONDONTWRITEBYTECODE,'1');}
 finally{if(before===undefined)delete process.env.__PYVENV_LAUNCHER__;else process.env.__PYVENV_LAUNCHER__=before;}
});
