'use strict';
// Integration check: real Electron networking, isolated cache, public metadata
// only. Invoke Electron with this script and an explicit --package=<path>.
const {app,net,session}=require('electron');
process.on('uncaughtException',error=>{process.stderr.write(error.message+'\n');app.exit(1);});
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-network-acceptance-'));app.setPath('userData',profile);
const packageArgument=process.argv.find(value=>value.startsWith('--package='));
if(!packageArgument)throw new Error('An explicit prepared package.json is required');
const config=JSON.parse(fs.readFileSync(packageArgument.slice('--package='.length),'utf8')).desktopAppConfig;
const network=require('../network-transport.cjs'),{GitHubModuleTransport}=require('../github-module-transport.cjs'),protocol=require('../github-module-protocol.cjs');
const timer=setTimeout(()=>{process.stderr.write('Native metadata acceptance timed out\n');app.exit(1);},90000);
app.whenReady().then(async()=>{
 assert.equal(app.isReady(),true);network.configureElectronTransport(net);
 const proxy=await session.defaultSession.resolveProxy('https://github.com');
 const result={electron:process.versions.electron,configuredAfterReady:app.isReady(),systemProxyResolved:Boolean(proxy),profileIsolated:app.getPath('userData')===profile,channels:[]};
 for(const channel of ['public-v1','workspace-v1']){
  const transport=new GitHubModuleTransport('mentat',{channel});
  const checked=protocol.pointer('mentat',protocol.parseJson(await transport.currentPointer()),config.desktopAccessTrust.updatePublicKeysByApp.mentat,{},channel);
  const bytes=await transport.manifest(checked.value);
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),checked.value.manifest.sha256);
  result.channels.push({channel,pointerSignatureVerified:true,manifestHashVerified:true,manifestBytes:bytes.length,releaseTag:checked.value.releaseTag});
 }
 process.stdout.write(JSON.stringify(result)+'\n');clearTimeout(timer);app.quit();
}).catch(error=>{clearTimeout(timer);process.stderr.write(JSON.stringify({error:error.message,reason:error.reason||null})+'\n');app.exit(1);});
