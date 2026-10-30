'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),{EventEmitter}=require('node:events'),{Readable}=require('node:stream');
const {createElectronRequest,classifyNetworkError,request,configureElectronTransport}=require('../network-transport.cjs');
function fixture(handler){const calls=[];const net={request:options=>{const native=new EventEmitter();native.end=()=>queueMicrotask(()=>handler(native,options));native.abort=()=>{native.aborted=true;native.emit('close');};calls.push({native,options});return native;}};return {calls,send:createElectronRequest(net)};}
function open(send,options={}){let req;const response=new Promise((resolve,reject)=>{req=send('https://github.com/owner/repo',options,resolve);req.once('error',reject);req.end();});return {response,get req(){return req;}};}
function incoming(native,bytes,headers={}){const res=Readable.from([bytes]);res.statusCode=200;res.headers=headers;native.emit('response',res);return res;}
async function body(stream){const chunks=[];for await(const chunk of stream)chunks.push(chunk);return Buffer.concat(chunks);}

test('native public requests use OS network stack with origin credentials omitted and identity encoding',async()=>{
 const f=fixture(native=>incoming(native,Buffer.from('abc'),{'content-length':['3']}));
 const stream=await open(f.send,{method:'GET',rejectUnauthorized:true,headers:{Range:'bytes=4-'}}).response;
 assert.equal((await body(stream)).toString(),'abc');assert.equal(stream.headers['content-length'],'3');
 const o=f.calls[0].options;assert.equal(o.redirect,'manual');assert.equal(o.credentials,'omit');assert.equal(o.useSessionCookies,false);assert.equal(o.cache,'no-cache');assert.equal(o.bypassCustomProtocolHandlers,true);assert.equal(o.headers.Range,'bytes=4-');assert.equal(o.headers['Accept-Encoding'],'identity');
 for(const options of [{rejectUnauthorized:false},{method:'POST'},{headers:{Cookie:'private'}},{headers:{Authorization:'secret'}},{headers:{'Proxy-Authorization':'secret'}},{headers:{'Accept-Encoding':'gzip'}}])assert.throws(()=>f.send('https://github.com/x',options,()=>{}));
 for(const url of ['http://github.com/x','https://user:secret@github.com/x','file:///secret','https://github.com:8443/x'])assert.throws(()=>f.send(url,{},()=>{}));
});
test('manual redirects are reported to caller without following and reject ambiguous/oversize locations',async()=>{
 const f=fixture(native=>native.emit('redirect',302,'GET','https://release-assets.githubusercontent.com/public',{location:['https://release-assets.githubusercontent.com/public']}));
 const stream=await open(f.send).response;assert.equal(stream.statusCode,302);assert.equal(stream.headers.location,'https://release-assets.githubusercontent.com/public');assert.equal((await body(stream)).length,0);assert.equal(f.calls.length,1);assert.equal(f.calls[0].native.aborted,true);
 for(const headers of [{location:['https://evil.invalid','https://other.invalid']},{location:['https://evil.invalid']}]){const g=fixture(native=>native.emit('redirect',302,'GET','https://github.com/public',headers));await assert.rejects(open(g.send).response,/Ambiguous/);}
 const huge=fixture(native=>native.emit('redirect',302,'GET','https://github.com/'+ 'x'.repeat(8192),{}));await assert.rejects(open(huge.send).response,/Ambiguous/);
});
test('certificate failures remain closed; explicit native network/proxy failures carry bounded retry metadata',async()=>{
 for(const [code,reason]of [['ERR_PROXY_CONNECTION_FAILED','proxy'],['ERR_NAME_NOT_RESOLVED','unreachable'],['ERR_CONNECTION_RESET','unreachable'],['ERR_CONNECTION_CLOSED','unreachable'],['ERR_TIMED_OUT','timeout']]){
  const f=fixture(native=>native.emit('error',new Error('net::'+code)));await assert.rejects(open(f.send).response,error=>error.reason===reason&&error.retryableNetwork===true&&error.retryAfterMs===1000);
 }
 const tls=new Error('net::ERR_CERT_AUTHORITY_INVALID'),f=fixture(native=>native.emit('error',tls));await assert.rejects(open(f.send).response,error=>error===tls&&error.retryableNetwork!==true);assert.equal(classifyNetworkError(Object.assign(new Error('wrong certificate'),{code:'ERR_TLS_CERT_ALTNAME_INVALID'})).retryableNetwork,undefined);
});
test('unresolved proxy authentication defers without collecting credentials or leaking origin authentication',async()=>{
 for(const isProxy of [true,false]){let credentials;const f=fixture(native=>native.emit('login',{isProxy},(...args)=>{credentials=args;}));await assert.rejects(open(f.send).response,error=>isProxy?error.reason==='proxy'&&error.retryableNetwork===true:error.retryableNetwork!==true);assert.deepEqual(credentials,[]);}
});
test('writable close does not cancel later headers or truncate buffered response bytes',async()=>{
 for(const early of [true,false]){const f=fixture(native=>{if(early)native.emit('close');incoming(native,Buffer.from('buffered complete response'));if(!early)native.emit('close');});assert.equal((await body(await open(f.send).response)).toString(),'buffered complete response');}
});
test('duplicate native headers reject before exposing a response, without an unhandled stream error',async()=>{
 const f=fixture(native=>incoming(native,Buffer.from('unsafe'),{'Content-Length':'6','content-length':'7'}));await assert.rejects(open(f.send).response,/Ambiguous/);await new Promise(resolve=>setImmediate(resolve));assert.equal(f.calls[0].native.aborted,true);
});
test('a caller refusing response framing aborts the native body before piping into a destroyed readable',async()=>{
 const f=fixture(native=>incoming(native,Buffer.from('refused body')));await new Promise((resolve,reject)=>{const req=f.send('https://github.com/owner/repo',{},stream=>{stream.destroy();resolve();});req.once('error',reject);req.end();});await new Promise(resolve=>setImmediate(resolve));assert.equal(f.calls[0].native.aborted,true);
});
test('destroy cancels an owned header wait and a partially consumed response',async()=>{
 const f=fixture(()=>{}),waiting=open(f.send);waiting.req.destroy(Object.assign(new Error('cancel'),{reason:'cancelled'}));await assert.rejects(waiting.response,/cancel/);assert.equal(f.calls[0].native.aborted,true);
 let nativeBody;const g=fixture(native=>{nativeBody=new Readable({read(){}});nativeBody.statusCode=200;nativeBody.headers={};native.emit('response',nativeBody);nativeBody.push(Buffer.from('part'));});const transfer=open(g.send),stream=await transfer.response;stream.destroy();await new Promise(resolve=>setImmediate(resolve));assert.equal(g.calls[0].native.aborted,true);nativeBody.destroy();
});
test('native response backpressure bounds buffering while preserving every delivered byte',async()=>{
 let remaining=1024*1024;const f=fixture(native=>{const source=new Readable({highWaterMark:16384,read(){while(remaining){const n=Math.min(remaining,16384);remaining-=n;if(!this.push(Buffer.alloc(n,7)))return;}this.push(null);}});source.statusCode=200;source.headers={};native.emit('response',source);});
 const stream=await open(f.send).response;await new Promise(resolve=>setImmediate(resolve));assert(stream.readableLength<=128*1024);const bytes=await body(stream);assert.equal(bytes.length,1024*1024);assert(bytes.every(value=>value===7));
});
test('only headless Node has a fallback; unconfigured Electron fails closed',()=>{
 const https=require('node:https'),original=https.request;https.request=()=>({headless:true});try{assert.equal(request('https://github.com',{},()=>{}).headless,true);}finally{https.request=original;}
 const previous=Object.getOwnPropertyDescriptor(process.versions,'electron');Object.defineProperty(process.versions,'electron',{value:'44.7.2',configurable:true});
 try{assert.throws(()=>request('https://github.com',{},()=>{}),/not configured/);configureElectronTransport({request:()=>new EventEmitter()});assert.throws(()=>configureElectronTransport({request(){}}),/already configured/);}finally{if(previous)Object.defineProperty(process.versions,'electron',previous);else delete process.versions.electron;}
});
