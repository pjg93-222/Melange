'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {EventEmitter}=require('node:events');
const {Readable}=require('node:stream');
const {GitHubModuleTransport}=require('../github-module-transport.cjs');
function fixture(handler,options={}){
 const calls=[];
 const request=(url,options,callback)=>{const req=new EventEmitter();req.destroy=()=>{req.destroyed=true;};req.end=()=>queueMicrotask(()=>handler({url,options,req,respond:(status,body='',headers={})=>{const bytes=Buffer.isBuffer(body)?body:Buffer.from(body);const incoming=Readable.from([bytes]);incoming.statusCode=status;incoming.headers={'content-length':String(bytes.length),...headers};callback(incoming);}}));calls.push({url,options,req});return req;};
 return {calls,transport:new GitHubModuleTransport('mentat',{request,...options})};
}
const tag='module-data-2026-10-21-fixture',commit='a'.repeat(40);
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
