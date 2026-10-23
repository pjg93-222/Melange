'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),http=require('node:http'),crypto=require('node:crypto');
const {startScrapeService,checkedQuery,checkedResponse}=require('../scrape-service.cjs');
const value={schemaVersion:1,provider:'fec',path:'schedules/schedule_a',query:{per_page:100}};
const body=Buffer.from('{ "amount": 123456789012345.123456 }\n');
const result={schemaVersion:1,provider:'fec',raw:{status:200,headers:{'content-type':'application/json'},bodyBase64:body.toString('base64'),bytes:body.length,sha256:crypto.createHash('sha256').update(body).digest('hex'),originalResponseBytes:true}};
function call(service,changes={}){return new Promise((resolve,reject)=>{const data=JSON.stringify(changes.value||value),request=http.request(service.url,{method:'POST',headers:{Authorization:'Bearer '+service.token,'Content-Type':'application/json','Content-Length':Buffer.byteLength(data),...changes.headers}},response=>{const chunks=[];response.on('data',part=>chunks.push(part));response.on('end',()=>resolve({status:response.statusCode,headers:response.headers,value:JSON.parse(Buffer.concat(chunks))}));});request.on('error',reject);request.end(data);});}
test('only a private native capability can collect; no browser access or provider credentials',async t=>{
 let calls=0,authorizations=0;const service=await startScrapeService({authorize:async()=>{authorizations++;},query:async()=>{calls++;return result;}});t.after(()=>service.close());
 assert.equal((await call(service,{headers:{Authorization:'Bearer '+('a'.repeat(43))}})).status,403);
 assert.equal((await call(service,{headers:{Origin:'https://example.org'}})).status,403);
 assert.equal((await call(service,{headers:{Host:'evil.example'}})).status,403);
 assert.equal((await call(service,{value:{...value,query:{api_key:'secret'}}})).status,503);
 assert.equal(calls,0);
 const response=await call(service);assert.equal(response.status,200);assert.deepEqual(response.value,result);assert.equal(calls,1);assert.equal(authorizations,2);
 assert.equal(Buffer.from(response.value.raw.bodyBase64,'base64').toString(),body.toString());
});
test('rate limits survive bridge and authorization changes discard completed responses',async t=>{
 let checks=0,mode='limit';const service=await startScrapeService({authorize:async()=>{checks++;if(mode==='revoke'&&checks===2)throw new Error('revoked');},query:async()=>{if(mode==='limit')throw Object.assign(new Error('sensitive upstream text'),{statusCode:429,retryAfter:17});return result;}});t.after(()=>service.close());
 const limited=await call(service);assert.equal(limited.status,429);assert.equal(limited.headers['retry-after'],'17');assert.equal(JSON.stringify(limited).includes('sensitive'),false);
 mode='revoke';checks=0;assert.equal((await call(service)).status,503);
});
test('closing native bridge aborts active authenticated request',async()=>{
 let started,aborted;const active=new Promise(resolve=>{started=resolve;}),stopped=new Promise(resolve=>{aborted=resolve;});
 const service=await startScrapeService({authorize:async()=>{},query:async(_value,{signal})=>{started();await new Promise(resolve=>signal.addEventListener('abort',()=>{aborted();resolve();},{once:true}));return result;}});
 const pending=call(service).catch(()=>null);await active;await service.close();await stopped;await pending;
});
test('raw response digest, byte length, headers and exact number bytes are verified',()=>{
 assert.equal(checkedResponse(result),result);
 for(const change of [{bytes:body.length+1},{sha256:'0'.repeat(64)},{originalResponseBytes:false},{headers:{authorization:'secret'}},{bodyBase64:result.raw.bodyBase64+' '}])assert.throws(()=>checkedResponse({...result,raw:{...result.raw,...change}}));
 for(const change of [{provider:'untrusted'},{path:'../private'},{path:'https://evil.invalid/'},{query:{url:'https://evil.invalid/'}}])assert.throws(()=>checkedQuery({...value,...change}));
});
