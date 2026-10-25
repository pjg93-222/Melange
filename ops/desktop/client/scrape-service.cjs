'use strict';
// Private backend-to-main bridge. Neither the access bearer nor provider API
// keys are exposed by this loopback capability or by renderer IPC.
const http=require('node:http'),crypto=require('node:crypto');
const BODY_LIMIT=16384,RESPONSE_LIMIT=24*1024**2;
function checkedQuery(value){
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join('|')!=='path|provider|query|schemaVersion'||value.schemaVersion!==1||!['fec','congress'].includes(value.provider)||typeof value.path!=='string'||value.path.length>240||!/^\w[\w/-]*$/.test(value.path)||value.path.includes('//')||!value.query||typeof value.query!=='object'||Array.isArray(value.query)||Buffer.byteLength(JSON.stringify(value))>BODY_LIMIT)throw new Error('Invalid collection request');
 if(Object.keys(value.query).some(key=>/^(api_?key|authorization|x-api-key|access_token|token|headers|url|callback|redirect|host)$/i.test(key)))throw new Error('Credentials are not collection parameters');
 return value;
}
function checkedResponse(value){
 const raw=value?.raw;
 if(!raw||typeof raw!=='object'||Array.isArray(raw)||Object.keys(raw).sort().join('|')!=='bodyBase64|bytes|headers|originalResponseBytes|sha256|status'||raw.originalResponseBytes!==true||!Number.isInteger(raw.status)||raw.status<200||raw.status>599||!Number.isInteger(raw.bytes)||raw.bytes<1||raw.bytes>16*1024**2||typeof raw.bodyBase64!=='string'||raw.bodyBase64.length>Math.ceil(16*1024**2/3)*4||typeof raw.sha256!=='string'||!/^[a-f0-9]{64}$/.test(raw.sha256)||!raw.headers||typeof raw.headers!=='object'||Array.isArray(raw.headers))throw new Error('Invalid shared collection response');
 const body=Buffer.from(raw.bodyBase64,'base64');
 if(body.length!==raw.bytes||body.toString('base64')!==raw.bodyBase64||crypto.createHash('sha256').update(body).digest('hex')!==raw.sha256||Object.entries(raw.headers).some(([key,val])=>!['content-type','date','last-modified','etag','retry-after'].includes(key)||typeof val!=='string'||val.length>1024||/[\r\n]/.test(val)))throw new Error('Invalid shared collection response');
 return value;
}
async function startScrapeService({query,authorize}={}){
 if(typeof query!=='function'||typeof authorize!=='function')throw new Error('Native collection authority is required');
 const token=crypto.randomBytes(32).toString('base64url'),credential=Buffer.from('Bearer '+token),active=new Set();let authority,closed=false;
 const server=http.createServer({maxHeaderSize:8192,headersTimeout:10000,requestTimeout:100000},async(req,res)=>{
  let controller,timer;const reply=(status,value,retry)=>{if(res.destroyed||res.writableEnded)return;res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store','Connection':'close',...(retry?{'Retry-After':String(retry)}:{})});res.end(JSON.stringify(value));};
  const disconnect=()=>{if(!res.writableEnded)controller?.abort();};
  try{
   const counts={};for(let i=0;i<req.rawHeaders.length;i+=2){const name=req.rawHeaders[i].toLowerCase();counts[name]=(counts[name]||0)+1;}
   const supplied=Buffer.from(req.headers.authorization||'');
   if(closed||req.method!=='POST'||req.url!=='/query'){reply(404,{error:'not_found'});return;}
   if(req.socket.remoteAddress!=='127.0.0.1'||counts.host!==1||req.headers.host!==authority||'origin' in req.headers||Object.keys(req.headers).some(k=>k.startsWith('sec-fetch-'))||counts.authorization!==1||supplied.length!==credential.length||!crypto.timingSafeEqual(supplied,credential)){reply(403,{error:'access_denied'});return;}
   if(counts['content-length']!==1||!/^[0-9]{1,5}$/.test(req.headers['content-length'])||Number(req.headers['content-length'])>BODY_LIMIT||counts['content-type']!==1||req.headers['content-type']!=='application/json'||req.headers['transfer-encoding']||req.headers['content-encoding']){reply(400,{error:'invalid_request'});return;}
   if(active.size>=4){reply(429,{error:'collection_busy'},5);return;}
   controller=new AbortController();active.add(controller);timer=setTimeout(()=>controller.abort(),95000);timer.unref();
   req.once('aborted',disconnect);res.once('close',disconnect);
   let bytes=0;const chunks=[];for await(const part of req){bytes+=part.length;if(bytes>BODY_LIMIT||controller.signal.aborted)throw new Error();chunks.push(part);}
   const value=checkedQuery(JSON.parse(Buffer.concat(chunks).toString('utf8')));await authorize();
   const result=await query(value,{signal:controller.signal});await authorize();
   if(controller.signal.aborted||Buffer.byteLength(JSON.stringify(result))>RESPONSE_LIMIT)throw new Error();
   reply(200,result);
  }catch(error){const code=[403,429,503].includes(error?.statusCode)?error.statusCode:503;reply(code,{error:code===429?'collection_rate_limited':'collection_unavailable'},error?.retryAfter);}
  finally{clearTimeout(timer);req.off('aborted',disconnect);res.off('close',disconnect);if(controller)active.delete(controller);}
 });
 server.maxConnections=8;server.maxRequestsPerSocket=1;server.keepAliveTimeout=1000;server.timeout=100000;
 server.on('timeout',socket=>socket.destroy());server.on('clientError',(_error,socket)=>socket.destroy());
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',()=>{server.off('error',reject);resolve();});});
 authority='127.0.0.1:'+server.address().port;
 return {url:'http://'+authority+'/query',token,close:async()=>{closed=true;for(const controller of active)controller.abort();await new Promise(resolve=>{server.close(resolve);server.closeAllConnections();});}};
}
module.exports={checkedQuery,checkedResponse,startScrapeService};
