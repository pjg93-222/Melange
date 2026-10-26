'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {canonical}=require('../../access-client.cjs');
const protocol=require('../../github-module-protocol.cjs');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function signed(appId='mentat',{registry,sequence=1,bytes=Buffer.from('{"aggregate":42}'),keys=crypto.generateKeyPairSync('ed25519')}={}){
 const kind=appId+'.fixture.v1';
 registry=registry||{[kind]:{appId,version:1,roles:{aggregate:{path:'models/aggregate.json',maxBytes:1024*1024}},maxTotalBytes:1024*1024,validateMetadata:()=>true,validateSnapshot:async({files})=>JSON.parse(fs.readFileSync(files.aggregate,'utf8')).aggregate===42}};
 const chunks=[bytes.subarray(0,Math.ceil(bytes.length/2)),bytes.subarray(Math.ceil(bytes.length/2))],objects=new Map();
 const dataset={datasetId:'10000000-0000-4000-8000-000000000001',revisionId:crypto.randomUUID(),kind,adapterVersion:1,objects:[{role:'aggregate',bytes:bytes.length,sha256:sha(bytes),segments:chunks.map((chunk,n)=>{const asset='aggregate-'+sequence+'-'+n+'.bin';objects.set(asset,chunk);return {asset,bytes:chunk.length,sha256:sha(chunk)};})}],counts:{files:1}};
 const app=protocol.configuration(appId),manifest={schemaVersion:1,purpose:app.purpose+'sets',appId,repository:app.repository,releaseTag:'module-data-2026-10-21-r'+sequence,datasets:[dataset]};
 const value={schemaVersion:1,purpose:app.purpose,appId,repository:app.repository,catalogSequence:sequence,releaseTag:manifest.releaseTag,releaseCommit:'a'.repeat(40),manifest:{asset:'manifest.json',bytes:0,sha256:''}};
 const publicKeys={fixture:keys.publicKey.export({format:'der',type:'spki'}).subarray(-32).toString('base64')};
 const sign=body=>{const raw=Buffer.from(canonical(body));return {schemaVersion:1,keyId:'fixture',payload:raw.toString('base64'),signature:crypto.sign(null,raw,keys.privateKey).toString('base64')};};
 const result={appId,keys,publicKeys,registry,objects,manifest,value,sign,bytes};
 result.rebind=()=>{result.manifestBytes=Buffer.from(canonical(manifest));value.manifest={asset:'manifest.json',bytes:result.manifestBytes.length,sha256:sha(result.manifestBytes)};result.envelope=sign(value);return result;};
 return result.rebind();
}
function environment(appId='mentat'){
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'github-module-fixture-')),profile=path.join(temporary,'profile'),original=path.join(temporary,'original');fs.mkdirSync(profile);fs.mkdirSync(original);
 const selected={dataDirectory:original},grant={appId,grantId:'20000000-0000-4000-8000-000000000001',serverId:'20000000-0000-4000-8000-000000000002',deviceId:'20000000-0000-4000-8000-000000000003',principalId:'20000000-0000-4000-8000-000000000004',accountIdentity:'fixture@example.invalid'};
 let revoked=false,owner=true,journal=null,remote=signed(appId),network=null;const offsets=[],requests=[];
 const authorize=async()=>({accepted:{revoked,grant},owner:owner?{mode:'existing-owner',appId,grantId:grant.grantId,accountIdentity:grant.accountIdentity,dataBindings:[{districtId:null,dataRootHash:sha(Buffer.from(original)),localUserId:null,localUsername:null}]}:null});
 const transport={
  resolveMain:async()=>{requests.push('main');if(network)throw protocol.fail(network,'Synthetic network unavailable');return 'b'.repeat(40);},
  pointer:async()=>{requests.push('pointer');return Buffer.from(canonical(remote.envelope));},
  verifyRelease:async()=>{requests.push('release');return true;},
  manifest:async()=>{requests.push('manifest');return remote.manifestBytes;},
  segment:async(_tag,item,{offset,onChunk})=>{requests.push(item.asset);offsets.push(offset);const raw=remote.objects.get(item.asset);for(let n=offset;n<raw.length;n+=3)await onChunk(raw.subarray(n,Math.min(n+3,raw.length)));return raw.length-offset;}
 };
 const store={read:async()=>journal===null?null:structuredClone(journal),write:async value=>{journal=structuredClone(value);}};
 const options={appId,profile,cacheRoot:path.join(profile,'packs','github-module-data'),publicKeys:remote.publicKeys,registry:remote.registry,authorize,transport,store,minimumFreeBytes:0,effectiveConfiguration:({originalSelected,source})=>({...originalSelected,ownerGitHubModuleData:source})};
 return {temporary,profile,original,selected,grant,transport,store,options,offsets,requests,get journal(){return journal;},get remote(){return remote;},set remote(value){remote=value;},set revoked(value){revoked=value;},set owner(value){owner=value;},set network(value){network=value;},cleanup(){const resolved=path.resolve(temporary);if(path.dirname(resolved)!==path.resolve(os.tmpdir())||!path.basename(resolved).startsWith('github-module-fixture-'))throw new Error('Unsafe fixture cleanup');fs.rmSync(resolved,{recursive:true,force:true});}};
}
function redirectedLocalCache(t,base,{physicalRoot=path.join(base,'Packages','fixture','LocalCache','Local','MelangeData')}={}){
 // Model transparent Windows package redirection, without a junction that the
 // production no-reparse policy must reject. All files remain generated.
 const lexicalRoot=path.join(base,'MelangeData');fs.mkdirSync(path.dirname(physicalRoot),{recursive:true});
 const map=file=>typeof file==='string'&&(file===lexicalRoot||file.startsWith(lexicalRoot+path.sep))?physicalRoot+file.slice(lexicalRoot.length):file;
 for(const name of ['existsSync','statSync','lstatSync']){const original=fs[name];t.mock.method(fs,name,function(file,...args){return original.call(this,map(file),...args);});}
 const native=fs.realpathSync.native;t.mock.method(fs.realpathSync,'native',function(file,...args){return native.call(this,map(file),...args);});
 for(const name of ['mkdir','lstat','realpath']){const original=fs.promises[name];t.mock.method(fs.promises,name,function(file,...args){return original.call(this,map(file),...args);});}
 return {lexicalRoot,physicalRoot,map};
}
module.exports={signed,environment,sha,redirectedLocalCache};
