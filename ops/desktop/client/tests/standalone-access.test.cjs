'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {createStandaloneGate}=require('../standalone-access.cjs');
const {LocalAccess}=require('../local-access.cjs');
const DEVICE='11111111-1111-4111-8111-111111111111';
const PASSWORD='Local-fixture-password-2026!';
function store(initial=null){let value=structuredClone(initial);return {read:async()=>structuredClone(value),write:async(...args)=>{value=structuredClone(args.at(-1));},delete:async()=>{value=null;},get value(){return structuredClone(value);}};}
function fixture(appId='melange'){
 const accountStore=store(),passwords=store(),devices=store();let time=1800000000000;
 return {accountStore,passwords,devices,advance:amount=>time+=amount,options:{appId,identity:{deviceId:DEVICE},accountStore,passwords,devices,configuration:()=>({district:'co-05'}),now:()=>time}};
}
const grant={schemaVersion:1,appId:'melange',serverId:'22222222-2222-4222-8222-222222222222',deviceId:DEVICE,principalId:'33333333-3333-4333-8333-333333333333',accountIdentity:'recipient_33333333333343338333333333333333',grantId:'44444444-4444-4444-8444-444444444444',role:'local_user',districtIds:[]};

test('fresh local account requires its password and never supplies remote approval',async()=>{
 const f=fixture(),gate=await createStandaloneGate(f.options);
 assert.equal((await gate.info()).phase,'needs_password');
 assert.equal(await gate.evidence(),null);assert.equal('client' in gate,false);
 await assert.rejects(gate.authorize(),/Local sign-in required/);
 for(const method of ['request','activate','poll'])await assert.rejects(gate.action(method,{}),/Unsupported local/);
 await gate.action('setPassword',{password:PASSWORD});
 assert.equal((await gate.info()).phase,'locked');await assert.rejects(gate.authorize(),/sign-in required/);
 await assert.rejects(gate.action('unlock',{password:'Incorrect-fixture-password!'}),/Incorrect password/);
 assert.equal(f.passwords.value.failures,1);
 await gate.action('unlock',{password:PASSWORD});
 const authorization=await gate.authorize();
 assert.equal(authorization.mode,'standalone');assert.equal(authorization.session.method,'local-password');
 assert.deepEqual(Object.keys(authorization).sort(),['identity','mode','principal','session']);
 assert.equal('accepted' in authorization,false);assert.equal('serverId' in authorization.identity,false);
 const next=await createStandaloneGate(f.options);
 assert.equal((await next.info()).phase,'ready');assert.equal((await next.authorize()).session.method,'device-trust');
 await next.action('lock');assert.equal(f.devices.value,null);assert.equal((await next.info()).phase,'locked');
 await assert.rejects(next.authorize(),/sign-in required/);
});

test('verified legacy password, throttling and device identity migrate without altering old records',async()=>{
 const f=fixture(),oldPasswords=store(),old=new LocalAccess({store:oldPasswords,now:f.options.now});
 await old.create(grant,PASSWORD);
 const passwordRecord={...oldPasswords.value,failures:4,blockedUntil:f.options.now()+5000,lastAttempt:f.options.now()};
 const binding=Object.fromEntries(['serverId','deviceId','principalId','accountIdentity','appId','grantId'].map(key=>[key,grant[key]]));
 const deviceRecord={schemaVersion:1,binding,verifiedAt:f.options.now()};
 const legacy={grant:structuredClone(grant),passwordRecord,deviceRecord,ownerVerified:false},before=structuredClone(legacy);
 const gate=await createStandaloneGate({...f.options,legacy});
 assert.equal(gate.identity.accountId,grant.principalId);assert.equal(gate.identity.accountIdentity,grant.accountIdentity);
 for(const key of ['salt','derivedKey','failures','blockedUntil','lastAttempt'])assert.equal(f.passwords.value[key],passwordRecord[key]);
 assert.equal((await gate.info()).phase,'ready');assert.deepEqual(legacy,before);
 await gate.action('lock');await assert.rejects(gate.action('unlock',{password:PASSWORD}),/Too many attempts/);
 f.advance(6000);await gate.action('unlock',{password:PASSWORD});assert.equal((await gate.info()).phase,'ready');
 assert.deepEqual(legacy,before);assert.equal(oldPasswords.value.derivedKey,passwordRecord.derivedKey);
});

test('partial migration retries with stable local identity and preserves original credentials',async()=>{
 const f=fixture(),realWrite=f.accountStore.write;let first=true;
 f.accountStore.write=async value=>{if(first){first=false;throw new Error('storage interrupted');}return realWrite(value);};
 const legacy={grant:structuredClone(grant),passwordRecord:null,deviceRecord:null,ownerVerified:true};
 await assert.rejects(createStandaloneGate({...f.options,legacy}),/storage interrupted/);
 const remembered=f.devices.value;
 const gate=await createStandaloneGate({...f.options,legacy});
 assert.deepEqual(f.devices.value,remembered);assert.equal((await gate.info()).phase,'ready');
 assert.equal(gate.identity.accountId,grant.principalId);
});

test('another device or damaged account cannot reset its way into local access',async()=>{
 const f=fixture();await createStandaloneGate(f.options);const original=f.accountStore.value;
 await assert.rejects(createStandaloneGate({...f.options,identity:{deviceId:'55555555-5555-4555-8555-555555555555'}}),/another installation/);
 assert.deepEqual(f.accountStore.value,original);
 await f.accountStore.write({...original,unexpected:true});
 await assert.rejects(createStandaloneGate(f.options),/Invalid protected local account/);
 const fresh=fixture();await assert.rejects(createStandaloneGate({...fresh.options,legacy:{grant:{...grant,deviceId:'55555555-5555-4555-8555-555555555555'}}}),/another installation/);
 assert.equal(fresh.accountStore.value,null);
});

test('foreign legacy device trust is refused rather than remembered',async()=>{
 const f=fixture();const binding=Object.fromEntries(['serverId','deviceId','principalId','accountIdentity','appId','grantId'].map(key=>[key,grant[key]]));
 binding.grantId='55555555-5555-4555-8555-555555555555';
 await assert.rejects(createStandaloneGate({...f.options,legacy:{grant,deviceRecord:{schemaVersion:1,binding,verifiedAt:f.options.now()},ownerVerified:false}}),/another account/);
 assert.equal(f.devices.value,null);assert.equal(f.accountStore.value,null);
});

test('Terrier local startup offers real backend sign-in without inventing staff credentials',async()=>{
 const f=fixture('terrier'),gate=await createStandaloneGate(f.options);
 assert.equal((await gate.info()).phase,'terrier_signin');
 const auth=await gate.authorize();assert.equal(auth.session,null);
 assert.deepEqual(auth.principal,{mode:'standalone',districtId:'co-05'});
 assert.equal('role' in auth.principal,false);assert.equal('accountIdentity' in auth.principal,false);
 assert.deepEqual(gate.districts(),['co-05','ct-01','or-05']);
 await assert.rejects(gate.authorize({district:'unsupported'}),/supported local district/);
 await assert.rejects(gate.action('setPassword',{password:PASSWORD}),/Unsupported local/);
 assert.equal(f.passwords.value,null);assert.equal(f.devices.value,null);
 assert.equal(await gate.evidence(),null);
});

test('an in-flight remembered-device read cannot undo a local lock',async()=>{
 const f=fixture();const gate=await createStandaloneGate({...f.options,legacy:{grant,ownerVerified:true}});
 let release;const originalRead=f.devices.read;f.devices.read=async identity=>{const record=await originalRead(identity);await new Promise(resolve=>{release=resolve;});return record;};
 const pending=gate.resume();while(!release)await new Promise(resolve=>setImmediate(resolve));
 gate.local.lock();release();assert.equal(await pending,null);assert.equal(gate.session,null);
});
