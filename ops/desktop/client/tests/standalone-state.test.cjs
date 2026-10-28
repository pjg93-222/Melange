'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {protectedLocalStores}=require('../standalone-state.cjs');
function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'standalone-state-fixture-')),profile=path.join(root,'profile'),key=crypto.randomBytes(32);let enabled=true,fail=false;
 const safeStorage={isEncryptionAvailable:()=>enabled,encryptString(value){if(fail)throw new Error('Synthetic encryption failure');const iv=crypto.randomBytes(12),cipher=crypto.createCipheriv('aes-256-gcm',key,iv),encrypted=Buffer.concat([cipher.update(value,'utf8'),cipher.final()]);return Buffer.concat([iv,cipher.getAuthTag(),encrypted]);},decryptString(value){const decipher=crypto.createDecipheriv('aes-256-gcm',key,value.subarray(0,12));decipher.setAuthTag(value.subarray(12,28));return Buffer.concat([decipher.update(value.subarray(28)),decipher.final()]).toString('utf8');}};
 const options={profile,appId:'melange',deviceId:'11111111-1111-4111-8111-111111111111',safeStorage,platform:'win32'};
 t.after(()=>{const resolved=path.resolve(root);if(path.dirname(resolved)!==path.resolve(os.tmpdir())||!path.basename(resolved).startsWith('standalone-state-fixture-'))throw new Error('Unsafe fixture cleanup');fs.rmSync(resolved,{recursive:true,force:true});key.fill(0);});
 return {root,profile,options,stores:protectedLocalStores(options),set enabled(value){enabled=value;},set fail(value){fail=value;}};
}
test('protected local records are encrypted and bound to scope, profile, app and device',async t=>{
 const f=fixture(t),value={privateFixture:'not-cleartext-fixture-987'};
 await f.stores.passwords.write({},value);const file=path.join(f.profile,'standalone-password.enc'),ciphertext=fs.readFileSync(file);
 assert.equal(ciphertext.includes(Buffer.from(value.privateFixture)),false);assert.deepEqual(await f.stores.passwords.read(),value);
 for(const changed of [{appId:'mentat'},{deviceId:'22222222-2222-4222-8222-222222222222'}])await assert.rejects(protectedLocalStores({...f.options,...changed}).passwords.read(),/another installation/);
 fs.copyFileSync(file,path.join(f.profile,'standalone-device.enc'));await assert.rejects(f.stores.devices.read(),/another installation/);
 const profile=path.join(f.root,'other');fs.mkdirSync(profile);fs.copyFileSync(file,path.join(profile,'standalone-password.enc'));await assert.rejects(protectedLocalStores({...f.options,profile}).passwords.read(),/another installation/);
 assert.deepEqual(fs.readFileSync(file),ciphertext);
});
test('ciphertext corruption and unavailable protection fail closed without replacing data',async t=>{
 const f=fixture(t);await f.stores.accountStore.write({fixture:1});const file=path.join(f.profile,'standalone-account.enc'),original=fs.readFileSync(file),damaged=Buffer.from(original);damaged[damaged.length-1]^=1;fs.writeFileSync(file,damaged);
 await assert.rejects(f.stores.accountStore.read());assert.deepEqual(fs.readFileSync(file),damaged);
 f.enabled=false;await assert.rejects(f.stores.accountStore.write({fixture:2}),/unavailable/);await assert.rejects(f.stores.accountStore.read(),/unavailable/);assert.deepEqual(fs.readFileSync(file),damaged);
});
test('failed atomic write preserves prior record and leaves old approval files alone',async t=>{
 const f=fixture(t);await f.stores.accountStore.write({fixture:1});const file=path.join(f.profile,'standalone-account.enc'),original=fs.readFileSync(file),legacy=path.join(f.profile,'legacy-approval.fixture');fs.writeFileSync(legacy,'preserved');
 f.fail=true;await assert.rejects(f.stores.accountStore.write({fixture:2}),/encryption failure/);f.fail=false;
 assert.deepEqual(fs.readFileSync(file),original);assert.deepEqual(await f.stores.accountStore.read(),{fixture:1});assert.equal(fs.readFileSync(legacy,'utf8'),'preserved');assert.equal(fs.readdirSync(f.profile).some(name=>name.endsWith('.tmp')),false);
});
