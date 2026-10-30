'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {EventEmitter}=require('node:events');
const {Readable}=require('node:stream');
const {GitHubModuleTransport,transferBudget,MAX_TRANSFER_MS}=require('../github-module-transport.cjs');
function fixture(handler,options={}){
 const calls=[];
 const request=(url,options,callback)=>{const req=new EventEmitter();req.destroy=()=>{req.destroyed=true;};req.end=()=>queueMicrotask(()=>handler({url,options,req,respond:(status,body='',headers={})=>{const bytes=Buffer.isBuffer(body)?body:Buffer.from(body);const incoming=Readable.from([bytes]);incoming.statusCode=status;incoming.headers={'content-length':String(bytes.length),...headers};callback(incoming);}}));calls.push({url,options,req});return req;};
 return {calls,transport:new GitHubModuleTransport('mentat',{request,...options})};
}
const tag='module-data-2026-10-21-fixture',commit='a'.repeat(40);

test('current pointer retries only marked raw connectivity failure using identical fixed API raw ref/path',async()=>{
 const f=fixture(({url,options,req,respond})=>{
  if(url.hostname==='raw.githubusercontent.com'){req.emit('error',Object.assign(new Error('offline'),{code:'ENOTFOUND'}));return;}
  assert.equal(options.headers.Accept,'application/vnd.github.raw+json');respond(200,'{"signed":"opaque"}');
 },{channel:'workspace-v1'});
 assert.equal((await f.transport.currentPointer()).toString(),'{"signed":"opaque"}');
 assert.deepEqual(f.calls.map(call=>call.url.href),[
  'https://raw.githubusercontent.com/pjg93-222/mentat/desktop-workspace-data/docs/desktop-workspace/current.json',
  'https://api.github.com/repos/pjg93-222/mentat/contents/docs/desktop-workspace/current.json?ref=desktop-workspace-data']);
 for(const url of ['https://api.github.com/repos/pjg93-222/mentat/contents/docs/desktop-workspace/current.json?ref=main',
  'https://api.github.com/repos/other/private/contents/docs/desktop-workspace/current.json?ref=desktop-workspace-data',
  'https://api.github.com/repos/pjg93-222/mentat/contents/secrets.json?ref=desktop-workspace-data'])
  await assert.rejects(f.transport.fetch(url,{limit:32768,pointerRaw:true}),{reason:'integrity'});
 assert.equal(f.calls.length,2);
});

test('pointer certificate, policy, missing-file, proxy, malformed and redirect failures never trigger API fallback',async()=>{
 for(const kind of ['tls','403','404','407','302','framing']){
  const f=fixture(({req,respond})=>{
   if(kind==='tls')req.emit('error',Object.assign(new Error('certificate'),{code:'CERT_HAS_EXPIRED'}));
   else if(kind==='framing')respond(200,'too large',{'content-length':'32769'});
   else respond(Number(kind),'refused',kind==='302'?{location:'https://api.github.com/repos/pjg93-222/mentat/contents/docs/desktop-data/current.json?ref=main'}:{});
  });
  await assert.rejects(f.transport.currentPointer());assert.equal(f.calls.length,1,kind);
 }
 const bytes=fixture(({respond})=>respond(200,'not a signed JSON envelope'));
 assert.equal((await bytes.transport.currentPointer()).toString(),'not a signed JSON envelope');assert.equal(bytes.calls.length,1);
});

test('API fallback quota does not block recovered raw pointer while each origin retains its own throttle',async()=>{
 let offline=true,now=100000;
 const f=fixture(({url,req,respond})=>{
  if(url.hostname==='raw.githubusercontent.com'&&offline){req.emit('error',Object.assign(new Error('offline'),{code:'ECONNRESET'}));return;}
  if(url.hostname==='api.github.com'){respond(429,'',{'retry-after':'60'});return;}
  respond(200,'{}');
 },{now:()=>now,random:()=>0});
 await assert.rejects(f.transport.currentPointer(),{reason:'rate_limited'});assert.equal(f.calls.length,2);
 offline=false;assert.equal((await f.transport.currentPointer()).toString(),'{}');assert.equal(f.calls.length,3);
 offline=true;await assert.rejects(f.transport.currentPointer(),{reason:'rate_limited'});assert.equal(f.calls.length,4);
 now+=61000;await assert.rejects(f.transport.currentPointer(),{reason:'rate_limited'});assert.equal(f.calls.length,6);
 const raw=fixture(({respond})=>respond(429,'',{'retry-after':'60'}),{now:()=>100000,random:()=>0});
 await assert.rejects(raw.transport.currentPointer(),{reason:'rate_limited'});await assert.rejects(raw.transport.currentPointer(),{reason:'rate_limited'});assert.equal(raw.calls.length,1);
});
test('large segment budget follows signed remaining size and is bounded separately from idle time',()=>{
 assert(transferBudget(256*1024**2)>120000);assert.equal(transferBudget(1024**3),MAX_TRANSFER_MS);assert.equal(transferBudget(1),120000);assert(transferBudget(64*1024**2)>=transferBudget(1024));
});
test('paced body progress refreshes idle budget and slow local writes do not masquerade as network idleness',async()=>{
 const {PassThrough}=require('node:stream');let interval;
 const request=(_url,_options,callback)=>{const req=new EventEmitter();req.destroy=()=>clearInterval(interval);req.end=()=>queueMicrotask(()=>{const res=new PassThrough();res.statusCode=200;res.headers={'content-length':'5'};callback(res);let n=0;interval=setInterval(()=>{res.write(Buffer.from('x'));if(++n===5){clearInterval(interval);res.end();}},40);});return req;};
 const transport=new GitHubModuleTransport('mentat',{request});let received=0;
 assert.equal(await transport.fetch('https://github.com/pjg93-222/mentat/releases/download/'+tag+'/part.bin',{asset:true,limit:5,expectedBytes:5,deadlineMs:2000,idleMs:150,onChunk:async chunk=>{received+=chunk.length;}}),5);assert.equal(received,5);
 const f=fixture(({respond})=>respond(200,'ab'));assert.equal(await f.transport.fetch('https://github.com/pjg93-222/mentat/releases/download/'+tag+'/part.bin',{asset:true,limit:2,expectedBytes:2,deadlineMs:2000,idleMs:50,onChunk:async()=>new Promise(resolve=>setTimeout(resolve,120))}),2);
});
test('a stalled transfer and a finite total budget both cancel the owned stream with a branded retry reason',async()=>{
 const {PassThrough}=require('node:stream');
 for(const active of [false,true]){let interval,body,request;const send=(_url,_options,callback)=>{request=new EventEmitter();request.destroy=()=>{request.destroyed=true;clearInterval(interval);};request.end=()=>queueMicrotask(()=>{body=new PassThrough();body.statusCode=200;body.headers={};callback(body);body.write(Buffer.from('x'));if(active)interval=setInterval(()=>body.write(Buffer.from('x')),20);});return request;};
  const transport=new GitHubModuleTransport('mentat',{request:send});await assert.rejects(transport.fetch('https://github.com/pjg93-222/mentat/releases/download/'+tag+'/part.bin',{asset:true,limit:10000,deadlineMs:active?100:2000,idleMs:60,onChunk:async()=>{}}),error=>error.reason==='timeout'&&error.retryableNetwork===true&&error.retryAfterMs>=1000);assert.equal(request.destroyed,true);assert.equal(body.destroyed,true);
 }
});
test('paged Melange channel has a separate fixed pointer and cannot alter legacy routing',async()=>{
 const legacy=new GitHubModuleTransport('melange'),paged=new GitHubModuleTransport('melange',{paged:true});
 const calls=[];paged.fetch=async url=>{calls.push(url);return Buffer.from('{}');};
 await paged.pointer(commit);assert.equal(calls[0],'https://raw.githubusercontent.com/pjg93-222/melange/'+commit+'/docs/desktop-data/on-demand-current.json');
 assert.equal(legacy.pointerPath,'docs/desktop-data/current.json');
 assert.throws(()=>new GitHubModuleTransport('mentat',{paged:true}),/channel/);
 await assert.rejects(legacy.fetch(calls[0],{limit:100}),error=>error.reason==='integrity');
});
test('fixed public API/raw routes use normal TLS and no credentials or cookies',async()=>{
 const f=fixture(({url,respond})=>respond(200,url.hostname==='api.github.com'?JSON.stringify({ref:'refs/heads/main',object:{type:'commit',sha:commit}}):'{}'));
 assert.equal(await f.transport.resolveMain(),commit);assert.equal((await f.transport.pointer(commit)).toString(),'{}');
 assert.equal(f.calls[0].url.href,'https://api.github.com/repos/pjg93-222/mentat/git/ref/heads/main');assert.equal(f.calls[1].url.href,'https://raw.githubusercontent.com/pjg93-222/mentat/'+commit+'/docs/desktop-data/current.json');
 for(const {options,url} of f.calls){assert.equal(options.rejectUnauthorized,true);assert.equal(options.agent,false);assert.equal(url.username,'');assert.equal(url.password,'');assert.deepEqual(Object.keys(options.headers).filter(k=>/authorization|cookie|token|device|principal/i.test(k)),[]);assert.equal(options.headers['Accept-Encoding'],'identity');}
 for(const url of ['https://api.github.com/repos/other/private/commits/main','https://raw.githubusercontent.com/other/private/'+commit+'/docs/desktop-data/current.json','https://api.github.com/repos/pjg93-222/mentat/../../private','https://api.github.com/repos/pjg93-222/mentat/issues'])await assert.rejects(f.transport.fetch(url,{limit:100}),error=>error.reason==='integrity');
 assert.equal(f.calls.length,2);
});
test('asset redirects are bounded, HTTPS-only and never receive auth on any hop',async()=>{
 const f=fixture(({url,respond})=>url.hostname==='github.com'?respond(302,'',{location:'https://release-assets.githubusercontent.com/fixture?public-download=1'}):respond(200,'data'));
 assert.equal((await f.transport.manifest({releaseTag:tag,manifest:{asset:'manifest.json',bytes:4}})).toString(),'data');assert.equal(f.calls.length,2);
 for(const call of f.calls)assert.ok(!Object.keys(call.options.headers).some(key=>/authorization|cookie/i.test(key)));
 for(const location of ['http://release-assets.githubusercontent.com/file','https://evil.invalid/file','https://user:secret@release-assets.githubusercontent.com/file','https://release-assets.githubusercontent.com:444/file','https://github.com/other/repository/releases/download/'+tag+'/file']){const g=fixture(({respond})=>respond(302,'',{location}));await assert.rejects(g.transport.manifest({releaseTag:tag,manifest:{asset:'manifest.json',bytes:4}}),error=>error.reason==='integrity');assert.equal(g.calls.length,1);}
 const loop=fixture(({respond})=>respond(302,'',{location:'https://release-assets.githubusercontent.com/loop'}));await assert.rejects(loop.transport.manifest({releaseTag:tag,manifest:{asset:'manifest.json',bytes:4}}),/redirect/);assert.equal(loop.calls.length,4);
});

test('malformed asset redirect locations have an integrity reason and never make a second request',async()=>{
 for(const location of ['https://','https://[broken']){
  const f=fixture(({respond})=>respond(302,'',{location}));
  await assert.rejects(f.transport.manifest({releaseTag:tag,manifest:{asset:'manifest.json',bytes:4}}),error=>error.reason==='integrity');
  assert.equal(f.calls.length,1);
 }
});
test('API redirects and malformed/duplicate JSON fail verification without another host request',async()=>{
 const redirect=fixture(({respond})=>respond(302,'',{location:'https://evil.invalid'}));await assert.rejects(redirect.transport.resolveMain(),error=>error.reason==='integrity');assert.equal(redirect.calls.length,1);
 const duplicate=fixture(({respond})=>respond(200,'{"sha":"'+commit+'","sha":"'+commit+'"}'));await assert.rejects(duplicate.transport.resolveMain(),error=>error.reason==='integrity');
});
test('segment resume requires exact status, remaining length and Content-Range',async()=>{
 const f=fixture(({respond})=>respond(206,'cd',{'content-range':'bytes 2-3/4'}));const chunks=[];
 assert.equal(await f.transport.segment(tag,{asset:'part.bin',bytes:4},{offset:2,onChunk:async chunk=>chunks.push(chunk)}),2);assert.equal(Buffer.concat(chunks).toString(),'cd');assert.equal(f.calls[0].options.headers.Range,'bytes=2-');
 for(const headers of [{'content-range':'bytes 1-2/4'},{'content-range':'bytes 2-3/5'},{'content-range':'bytes 2-3/4','content-length':undefined},{'content-range':'bytes 2-3/4','content-length':'3'},{'content-range':'bytes 2-3/4','content-encoding':'gzip'}]){const g=fixture(({respond})=>respond(206,'cd',headers));await assert.rejects(g.transport.segment(tag,{asset:'part.bin',bytes:4},{offset:2,onChunk:async()=>{}}),error=>error.reason==='integrity');}
 const wrongStatus=fixture(({respond})=>respond(200,'abcd'));await assert.rejects(wrongStatus.transport.segment(tag,{asset:'part.bin',bytes:4},{offset:2,onChunk:async()=>{}}),error=>error.reason==='integrity');
});
test('exact byte bounds reject short/long and transfer-framing ambiguity',async()=>{
 for(const [body,headers] of [['toolong',{'content-length':'4'}],['abc',{'content-length':'4'}],['data',{'transfer-encoding':'chunked'}]]){const f=fixture(({respond})=>respond(200,body,headers));await assert.rejects(f.transport.manifest({releaseTag:tag,manifest:{asset:'manifest.json',bytes:4}}),error=>error.reason==='integrity');}
});
test('only known network failures are eligible for an offline reason; TLS failure is verification failure',async()=>{
 for(const [code,reason] of [['ENOTFOUND','unreachable'],['ECONNRESET','unreachable'],['CERT_HAS_EXPIRED','integrity'],['ERR_TLS_CERT_ALTNAME_INVALID','integrity']]){const f=fixture(({req})=>req.emit('error',Object.assign(new Error('synthetic-no-secret'),{code})));await assert.rejects(f.transport.resolveMain(),error=>error.reason===reason);}
 for(const [status,headers,reason] of [[429,{},'rate_limited'],[403,{'x-ratelimit-remaining':'0'},'rate_limited'],[503,{},'unreachable'],[403,{},'integrity'],[404,{},'integrity']]){const f=fixture(({respond})=>respond(status,'',headers));await assert.rejects(f.transport.resolveMain(),error=>error.reason===reason);}
});

test('primary and secondary quota responses retain deadlines and suppress repeated manual requests until expiry',async()=>{
 for(const [status,headers,seconds] of [[403,{'x-ratelimit-remaining':'0','x-ratelimit-reset':'1700000300'},300],
  [403,{'x-ratelimit-remaining':'24','retry-after':'120'},120],[429,{'retry-after':'120'},120]]){
  let now=1700000000000;
  const f=fixture(({respond})=>f.calls.length===1?respond(status,'',headers):respond(200,JSON.stringify({ref:'refs/heads/main',object:{type:'commit',sha:commit}})),{now:()=>now,random:()=>0});
  let first;await assert.rejects(f.transport.resolveMain(),error=>{first=error;return error.reason==='rate_limited';});
  assert.equal(first.githubRateLimit,true);assert.equal(first.retryAt,now+seconds*1000);assert.equal(first.retryAfter,headers['retry-after']);assert.equal(first.resetAt,headers['x-ratelimit-reset']);
  now=first.retryAt-1;await assert.rejects(f.transport.resolveMain(),error=>error.retryAt===first.retryAt&&error.reason==='rate_limited');assert.equal(f.calls.length,1);
  await assert.rejects(f.transport.fetch('https://api.github.com/repos/other/private/commits/main',{limit:100}),error=>error.reason==='integrity');
  const cancelled=new AbortController();cancelled.abort();await assert.rejects(f.transport.resolveMain({signal:cancelled.signal}),error=>error.reason==='cancelled');assert.equal(f.calls.length,1);
  now=first.retryAt;assert.equal(await f.transport.resolveMain(),commit);assert.equal(f.calls.length,2);
 }
});

test('known secondary-limit bodies use bounded classification while ordinary access denial remains closed',async()=>{
 for(const body of ['You have exceeded a secondary rate limit.','Abuse detection: try later.']){
  const f=fixture(({respond})=>respond(403,body,{'x-ratelimit-remaining':'24'}),{now:()=>1700000000000,random:()=>0});
  await assert.rejects(f.transport.resolveMain(),error=>error.reason==='rate_limited'&&error.retryAt===1700003600000);
  await assert.rejects(f.transport.resolveMain(),error=>error.reason==='rate_limited');assert.equal(f.calls.length,1);
 }
 for(const body of ['Resource not accessible','x'.repeat(8192)+'secondary rate limit']){
  const f=fixture(({respond})=>respond(403,body),{now:()=>1700000000000,random:()=>0});
  await assert.rejects(f.transport.resolveMain(),error=>error.reason==='integrity');assert.equal(f.transport.retry,null);
 }
});

test('an unfinished secondary-limit error body remains bounded by the original deadline and cancellation',async()=>{
 const {PassThrough}=require('node:stream');let request;
 const send=(_url,_options,callback)=>{request=new EventEmitter();request.destroy=()=>{request.destroyed=true;};request.end=()=>queueMicrotask(()=>{const body=new PassThrough();body.statusCode=403;body.headers={};callback(body);body.write('incomplete response');});return request;};
 const transport=new GitHubModuleTransport('mentat',{request:send});
 await assert.rejects(transport.fetch('https://api.github.com/repos/pjg93-222/mentat/git/ref/heads/main',{limit:100,deadlineMs:50}),error=>error.reason==='timeout');assert.equal(request.destroyed,true);assert.equal(transport.retry,null);
 const abort=new AbortController(),pending=transport.resolveMain({signal:abort.signal});await new Promise(resolve=>setImmediate(resolve));abort.abort();await assert.rejects(pending,error=>error.reason==='cancelled');assert.equal(request.destroyed,true);assert.equal(transport.retry,null);
});

test('a secondary-limit body stops at eight KiB without waiting for the server to finish',async()=>{
 const {PassThrough}=require('node:stream');
 for(const known of [true,false]){
  let request,body;
  const send=(_url,_options,callback)=>{request=new EventEmitter();request.destroy=()=>{request.destroyed=true;};request.end=()=>queueMicrotask(()=>{body=new PassThrough();body.statusCode=403;body.headers={};callback(body);body.write(Buffer.from((known?'secondary rate limit ':'')+'x'.repeat(8192)));});return request;};
  const transport=new GitHubModuleTransport('mentat',{request:send});
  await assert.rejects(transport.resolveMain(),error=>error.reason===(known?'rate_limited':'integrity'));
  assert.equal(request.destroyed,true);assert.equal(body.destroyed,true,'The capped response is closed without consuming its remainder');
 }
});
test('total deadline and abort cancel the owned request',async()=>{
 const f=fixture(()=>{});await assert.rejects(f.transport.fetch('https://api.github.com/repos/pjg93-222/mentat/git/ref/heads/main',{limit:100,deadlineMs:50}),error=>error.reason==='timeout');assert.equal(f.calls[0].req.destroyed,true);
 const g=fixture(()=>{}),abort=new AbortController(),pending=g.transport.resolveMain({signal:abort.signal});abort.abort();await assert.rejects(pending,error=>error.reason==='cancelled');assert.equal(g.calls[0].req.destroyed,true);
});
test('public prerelease and bounded annotated tag peel must bind to the exact signed commit',async()=>{
 const f=fixture(({url,respond})=>{const route=url.pathname;respond(200,JSON.stringify(route.includes('/releases/tags/')?{tag_name:tag,draft:false,prerelease:true}:route.includes('/git/ref/tags/')?{object:{type:'tag',sha:'b'.repeat(40)}}:{object:{type:'commit',sha:commit}}));});
 assert.equal(await f.transport.verifyRelease({releaseTag:tag,releaseCommit:commit}),true);assert.equal(f.calls.length,3);
 for(const change of [{draft:true},{prerelease:false},{tag_name:'other'}]){const g=fixture(({respond})=>respond(200,JSON.stringify({tag_name:tag,draft:false,prerelease:true,...change})));await assert.rejects(g.transport.verifyRelease({releaseTag:tag,releaseCommit:commit}),error=>error.reason==='integrity');assert.equal(g.calls.length,1);}
 const cycle=fixture(({url,respond})=>respond(200,JSON.stringify(url.pathname.includes('/releases/tags/')?{tag_name:tag,draft:false,prerelease:true}:{object:{type:'tag',sha:'b'.repeat(40)}})));await assert.rejects(cycle.transport.verifyRelease({releaseTag:tag,releaseCommit:commit}),/annotated tag/);assert.equal(cycle.calls.length,3);
 const mismatch=fixture(({url,respond})=>respond(200,JSON.stringify(url.pathname.includes('/releases/tags/')?{tag_name:tag,draft:false,prerelease:true}:{object:{type:'commit',sha:'c'.repeat(40)}})));await assert.rejects(mismatch.transport.verifyRelease({releaseTag:tag,releaseCommit:commit}),/reviewed commit/);
});
