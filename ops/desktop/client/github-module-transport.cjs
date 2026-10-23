'use strict';
// Fixed public hosts only. This module never receives an access token, cookie,
// account identity, data-root path or caller-supplied URL.
const https=require('node:https');
const {configuration,parseJson,fail,requireValue,COMMIT,TAG,POINTER_PATH,assetName,integer,MAX_MANIFEST,MAX_SEGMENT}=require('./github-module-protocol.cjs');
const ASSET_HOSTS=new Set(['github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','github-releases.githubusercontent.com']);
const NETWORK=new Set(['ENOTFOUND','EAI_AGAIN','ECONNRESET','ECONNREFUSED','ETIMEDOUT','ENETUNREACH','EHOSTUNREACH','EPIPE']);
function canceled(signal){if(signal?.aborted)throw fail('cancelled','Module data transfer cancelled');}
function networkError(error){return error?.reason?error:fail(NETWORK.has(error?.code)?'unreachable':'integrity',NETWORK.has(error?.code)?'GitHub module data is unavailable':'GitHub module connection verification failed');}
class GitHubModuleTransport{
 constructor(appId,{request=https.request,paged=false}={}){requireValue(typeof paged==='boolean'&&(!paged||appId==='melange'),'Unsupported module data channel');this.appId=appId;this.app=configuration(appId);this.request=request;this.pointerPath=paged?'docs/desktop-data/on-demand-current.json':POINTER_PATH;}
 async fetch(url,{limit,expectedBytes,offset=0,totalBytes,signal,onChunk,asset=false,deadlineMs=15000}={}){
  requireValue(Number.isSafeInteger(limit)&&limit>=0&&limit<=MAX_SEGMENT&&Number.isSafeInteger(deadlineMs)&&deadlineMs>=50&&deadlineMs<=120000,'Invalid module transport bounds');
  canceled(signal);const deadline=Date.now()+deadlineMs;let target=new URL(url),redirects=0;
  const repo=this.app.repository,tag=TAG.source.slice(1,-1),commit=COMMIT.source.slice(1,-1);
  const api=new RegExp('^/repos/'+repo+'/(?:git/ref/heads/main|releases/tags/'+tag+'|git/ref/tags/'+tag+'|git/tags/'+commit+')$');
  requireValue(!target.search&&(asset?target.hostname==='github.com'&&target.pathname.startsWith('/'+repo+'/releases/download/'):target.hostname==='api.github.com'?api.test(target.pathname):target.hostname==='raw.githubusercontent.com'&&new RegExp('^/'+repo+'/'+commit+'/'+this.pointerPath.replaceAll('.','\\.')+'$').test(target.pathname)),'Invalid fixed module transport route');
  for(;;){
   requireValue(target.protocol==='https:'&&!target.username&&!target.password&&!target.hash&&(!target.port||target.port==='443'),'Invalid module transport destination');
   const allowed=asset?ASSET_HOSTS.has(target.hostname):['api.github.com','raw.githubusercontent.com'].includes(target.hostname);
   requireValue(allowed,'Invalid module transport host');
   if(asset&&target.hostname==='github.com')requireValue(target.pathname.startsWith('/'+repo+'/releases/download/'),'Cross-repository module redirect refused');
   const remaining=deadline-Date.now();if(remaining<=0)throw fail('timeout','GitHub module transfer timed out');
   const result=await this.once(target,{limit,expectedBytes,offset,totalBytes,signal,onChunk,asset,deadlineMs:remaining});
   if(!result.redirect)return result.bytes;
   requireValue(asset&&redirects++<3,'GitHub module redirect refused');
   try{target=new URL(result.redirect,target);}catch{throw fail('integrity','GitHub module redirect refused');}
  }
 }
 once(url,{limit,expectedBytes,offset,totalBytes,signal,onChunk,asset,deadlineMs}){
  return new Promise((resolve,reject)=>{
   let req,res,settled=false;
   const finish=(error,value)=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);res?.destroy();req?.destroy();error?reject(error):resolve(value);};
   const abort=()=>finish(fail('cancelled','Module data transfer cancelled'));
   const timer=setTimeout(()=>finish(fail('timeout','GitHub module transfer timed out')),deadlineMs);
   signal?.addEventListener('abort',abort,{once:true});
   if(signal?.aborted){abort();return;}
   const headers={'User-Agent':'Melange-Desktop-ModuleData/1','Accept':asset?'application/octet-stream':'application/vnd.github+json','Accept-Encoding':'identity',...(offset?{Range:'bytes='+offset+'-'}:{})};
   try{
    req=this.request(url,{method:'GET',headers,rejectUnauthorized:true,agent:false},incoming=>{
     res=incoming;
     if([301,302,303,307,308].includes(res.statusCode)){
      const location=res.headers.location;
      if(!asset||typeof location!=='string'||location.length>8192){finish(fail('integrity','GitHub module redirect refused'));return;}
      finish(null,{redirect:location});return;
     }
     if(res.statusCode===429||res.statusCode===403&&res.headers['x-ratelimit-remaining']==='0'){finish(fail('rate_limited','GitHub module checks are rate limited'));return;}
     if([500,502,503,504].includes(res.statusCode)){finish(fail('unreachable','GitHub module data is unavailable'));return;}
     if(res.statusCode!==(offset?206:200)){finish(fail('integrity','GitHub module request refused'));return;}
     const lengthText=res.headers['content-length'],length=lengthText===undefined?null:Number(lengthText),encoding=res.headers['content-encoding'];
     if(encoding!==undefined&&encoding!=='identity'||lengthText!==undefined&&(typeof lengthText!=='string'||!/^(0|[1-9][0-9]*)$/.test(lengthText)||!Number.isSafeInteger(length)||length>limit)||res.headers['transfer-encoding']&&lengthText!==undefined||expectedBytes!==undefined&&length!==expectedBytes){finish(fail('integrity','Invalid GitHub module response framing'));return;}
     if(offset&&res.headers['content-range']!==`bytes ${offset}-${totalBytes-1}/${totalBytes}`){finish(fail('integrity','Invalid GitHub module range'));return;}
     (async()=>{
      const chunks=[];let received=0;
      try{
       for await(const chunk of res){
        if(settled)return;canceled(signal);received+=chunk.length;
        if(received>limit||expectedBytes!==undefined&&received>expectedBytes)throw fail('integrity','GitHub module response exceeds its bound');
        if(onChunk)await onChunk(chunk);else chunks.push(Buffer.from(chunk));
       }
       if(received!==(expectedBytes??length??received))throw fail('integrity','GitHub module response is incomplete');
       finish(null,{bytes:onChunk?received:Buffer.concat(chunks)});
      }catch(error){finish(networkError(error));}
     })();
    });
    req.once('error',error=>finish(networkError(error)));req.end();
   }catch(error){finish(networkError(error));}
  });
 }
 async json(relative,{signal}={}){
  requireValue(typeof relative==='string'&&relative.startsWith('/repos/'+this.app.repository+'/'),'Invalid GitHub module API route');
  return parseJson(await this.fetch('https://api.github.com'+relative,{limit:1024**2,signal}));
 }
 async resolveMain({signal}={}){
  const value=await this.json('/repos/'+this.app.repository+'/git/ref/heads/main',{signal});
  requireValue(value.ref==='refs/heads/main'&&value.object?.type==='commit'&&typeof value.object.sha==='string'&&COMMIT.test(value.object.sha)&&value.object.sha!=='0'.repeat(40),'Invalid GitHub module source commit');return value.object.sha;
 }
 async pointer(commit,{signal}={}){
  requireValue(typeof commit==='string'&&COMMIT.test(commit)&&commit!=='0'.repeat(40),'Invalid GitHub module source commit');
  return this.fetch('https://raw.githubusercontent.com/'+this.app.repository+'/'+commit+'/'+this.pointerPath,{limit:32768,signal});
 }
 async verifyRelease(value,{signal}={}){
  requireValue(value&&TAG.test(value.releaseTag)&&COMMIT.test(value.releaseCommit),'Invalid module release binding');
  const tag=value.releaseTag,release=await this.json('/repos/'+this.app.repository+'/releases/tags/'+tag,{signal});
  requireValue(release.tag_name===tag&&release.draft===false&&release.prerelease===true,'GitHub module data requires a public data prerelease');
  let object=(await this.json('/repos/'+this.app.repository+'/git/ref/tags/'+tag,{signal})).object;
  const seen=new Set();let depth=0;
  while(object?.type==='tag'){
   requireValue(typeof object.sha==='string'&&COMMIT.test(object.sha)&&!seen.has(object.sha)&&depth++<8,'Invalid module annotated tag');seen.add(object.sha);
   object=(await this.json('/repos/'+this.app.repository+'/git/tags/'+object.sha,{signal})).object;
  }
  requireValue(object?.type==='commit'&&object.sha===value.releaseCommit,'GitHub module tag does not match reviewed commit');return true;
 }
 async manifest(value,{signal}={}){
  const item=value?.manifest;
  requireValue(item?.asset==='manifest.json'&&integer(item.bytes,MAX_MANIFEST)&&item.bytes>0&&TAG.test(value.releaseTag),'Invalid module manifest request');
  return this.fetch('https://github.com/'+this.app.repository+'/releases/download/'+value.releaseTag+'/'+item.asset,{asset:true,limit:item.bytes,expectedBytes:item.bytes,signal});
 }
 async segment(releaseTag,item,{offset=0,signal,onChunk}={}){
  requireValue(TAG.test(releaseTag)&&assetName(item?.asset)&&integer(item.bytes,MAX_SEGMENT)&&item.bytes>0&&integer(offset,item.bytes)&&offset<item.bytes&&typeof onChunk==='function','Invalid module segment request');
  return this.fetch('https://github.com/'+this.app.repository+'/releases/download/'+releaseTag+'/'+item.asset,{asset:true,limit:item.bytes-offset,expectedBytes:item.bytes-offset,offset,totalBytes:item.bytes,signal,onChunk,deadlineMs:120000});
 }
}
module.exports={GitHubModuleTransport,ASSET_HOSTS,NETWORK};
