'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {EventEmitter}=require('node:events');
const {Readable}=require('node:stream');
const {GitHubModuleTransport}=require('../github-module-transport.cjs');
function fixture(handler){
 const calls=[];
 const request=(url,options,callback)=>{const req=new EventEmitter();req.destroy=()=>{req.destroyed=true;};req.end=()=>queueMicrotask(()=>handler({url,options,req,respond:(status,body='',headers={})=>{const bytes=Buffer.isBuffer(body)?body:Buffer.from(body);const incoming=Readable.from([bytes]);incoming.statusCode=status;incoming.headers={'content-length':String(bytes.length),...headers};callback(incoming);}}));calls.push({url,options,req});return req;};
 return {calls,transport:new GitHubModuleTransport('mentat',{request})};
}
const tag='module-data-2026-10-21-fixture',commit='a'.repeat(40);
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
