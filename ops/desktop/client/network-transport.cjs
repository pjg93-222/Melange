'use strict';
// Production downloads explicitly use the previously deployed Node HTTPS path.
// TLS validation, anonymous requests and signed artifact checks remain required.
// The native adapter remains available for explicit transport tests; no request
// silently changes transport after a failure.
const https=require('node:https'),{EventEmitter}=require('node:events'),{PassThrough}=require('node:stream');
let configured=null;
const RETRYABLE=new Set(['timeout','unreachable','proxy','rate_limited']);
const CONNECTION=new Set(['ENOTFOUND','EAI_AGAIN','ECONNRESET','ECONNREFUSED','ETIMEDOUT','ENETUNREACH','EHOSTUNREACH','EPIPE','ERR_NAME_NOT_RESOLVED','ERR_INTERNET_DISCONNECTED','ERR_CONNECTION_RESET','ERR_CONNECTION_CLOSED','ERR_CONNECTION_REFUSED','ERR_ADDRESS_UNREACHABLE','ERR_NETWORK_CHANGED','ERR_CONNECTION_TIMED_OUT','ERR_TIMED_OUT','ERR_SOCKET_NOT_CONNECTED']);
const PROXY=new Set(['ERR_PROXY_CONNECTION_FAILED','ERR_TUNNEL_CONNECTION_FAILED','ERR_NO_SUPPORTED_PROXIES','ERR_MANDATORY_PROXY_CONFIGURATION_FAILED','ERR_PROXY_AUTH_UNSUPPORTED','ERR_PROXY_AUTH_REQUESTED']);
function networkFailure(reason,message,{retryAfterMs=1000}={}){
 if(!RETRYABLE.has(reason))throw new Error('Invalid retryable transport reason');
 return Object.assign(new Error(message),{reason,code:reason,retryableNetwork:true,retryAfterMs:Math.min(3600000,Math.max(1000,Number.isSafeInteger(retryAfterMs)?retryAfterMs:1000))});
}
function classifyNetworkError(error){
 if(error?.reason)return error;
 const code=typeof error?.code==='string'?error.code:/\bnet::([A-Z0-9_]+)\b/.exec(error?.message||'')?.[1];
 if(PROXY.has(code))return networkFailure('proxy','The configured system proxy is unavailable.');
 if(['ETIMEDOUT','ERR_CONNECTION_TIMED_OUT','ERR_TIMED_OUT'].includes(code))return networkFailure('timeout','The public download connection timed out.');
 if(CONNECTION.has(code))return networkFailure('unreachable','The public download host is unavailable.');
 // Certificate, HTTP framing and unknown failures are deliberately not branded
 // retryable. In particular, ERR_CERT_* never relaxes the TLS policy.
 return error;
}
function headers(value={}){
 const result=Object.create(null);
 for(const [name,items] of Object.entries(value)){const key=name.toLowerCase();if(Object.hasOwn(result,key))throw new Error('Ambiguous native response headers');result[key]=Array.isArray(items)&&items.length===1?items[0]:items;}
 return result;
}
function createElectronRequest(net){
 if(!net||typeof net.request!=='function')throw new Error('The native network stack is unavailable');
 return (url,options={},callback)=>{
  const target=new URL(url);if(target.protocol!=='https:'||target.username||target.password||target.hash||target.port&&target.port!=='443'||options.rejectUnauthorized===false||!['GET','HEAD'].includes(options.method||'GET'))throw new Error('Invalid public native request');
  if(typeof callback!=='function'||Object.keys(options.headers||{}).some(name=>/^(?:authorization|cookie|proxy-authorization)$/i.test(name)))throw new Error('Public downloads cannot carry application credentials');
  const requestHeaders={};for(const [key,value]of Object.entries(options.headers||{})){if(key.toLowerCase()==='accept-encoding'){if(value!=='identity')throw new Error('Public downloads require identity encoding');}else requestHeaders[key]=value;}requestHeaders['Accept-Encoding']='identity';
  const request=new EventEmitter();let native,response,idleTimer,idleMs=0,started=false,closed=false,finished=false,exposed=false;
  const clearIdle=()=>{clearTimeout(idleTimer);idleTimer=null;};
  const touch=()=>{clearIdle();if(idleMs&&!closed&&!finished)idleTimer=setTimeout(()=>request.emit('timeout'),idleMs);};
  const stop=(error)=>{
   if(closed)return;closed=true;clearIdle();
   if(response&&!response.destroyed)response.destroy(exposed?error:undefined);
   try{native?.abort();}catch{}
   if(error)queueMicrotask(()=>request.emit('error',classifyNetworkError(error)));
  };
  request.destroy=error=>{stop(error);return request;};request.abort=()=>request.destroy();
  request.setTimeout=(milliseconds,listener)=>{if(!Number.isSafeInteger(milliseconds)||milliseconds<0)throw new Error('Invalid native request timeout');idleMs=milliseconds;if(typeof listener==='function')request.once('timeout',listener);if(started)touch();return request;};
  request.end=(body)=>{
   if(started||closed||body!==undefined)throw new Error('Public native request cannot be written or restarted');started=true;
   try{
    // Omit origin credentials/cookies. Chromium still resolves the OS proxy and
    // negotiates its existing proxy authentication; no app credentials are used.
    native=net.request({url:target.href,method:options.method||'GET',headers:requestHeaders,redirect:'manual',credentials:'omit',useSessionCookies:false,bypassCustomProtocolHandlers:true,cache:'no-cache'});
    native.on('error',error=>{if(!closed&&!finished)stop(classifyNetworkError(error));});
    native.on('login',(info,answer)=>{answer();stop(info?.isProxy?networkFailure('proxy','The system proxy requires authentication.'):new Error('Public download unexpectedly requested authentication.'));});
    native.on('redirect',(status,_method,location,value)=>{
     if(closed||finished)return;
     // The caller sees, validates and follows the redirect as a NEW request.
     // Never call followRedirect: doing so could bypass its fixed-host policy.
     let parsed;try{parsed=headers(value);if(typeof location!=='string'||location.length>8192||parsed.location!==undefined&&(typeof parsed.location!=='string'||new URL(parsed.location,target).href!==new URL(location,target).href))throw new Error('Ambiguous native redirect');}catch(error){stop(error);return;}
     finished=true;clearIdle();response=new PassThrough();response.statusCode=status;response.headers={...parsed,location};
     exposed=true;callback(response);response.end();try{native.abort();}catch{}
    });
    native.on('response',incoming=>{
     if(closed||finished){incoming.destroy?.();return;}
     try{const parsed=headers(incoming.headers);response=new PassThrough({highWaterMark:64*1024});response.statusCode=incoming.statusCode;response.headers=parsed;}
     catch(error){incoming.destroy?.();stop(error);return;}
     incoming.on('data',touch);incoming.once('end',()=>{finished=true;clearIdle();});incoming.once('error',error=>stop(classifyNetworkError(error)));
     response.once('close',()=>{if(!finished&&!closed)stop();});
     touch();exposed=true;callback(response);if(!closed&&!response.destroyed)incoming.pipe(response);else{incoming.destroy?.();if(!closed)stop();}
    });
    // ClientRequest is also a Writable: its close is not a reliable response
    // completion signal in44.7.2. IncomingMessage end/error and the caller's
    // bounded header/idle/total timers own completion, including a headerless close.
    touch();native.end();
   }catch(error){stop(classifyNetworkError(error));}
   return request;
  };
  Object.defineProperty(request,'destroyed',{get:()=>closed});return request;
 };
}
function configureElectronTransport(net){if(configured)throw new Error('The native network stack is already configured');configured=createElectronRequest(net);}
function configureNodeTransport(){if(configured)throw new Error('The network stack is already configured');configured=https.request.bind(https);}
function request(url,options,callback){if(configured)return configured(url,options,callback);if(process.versions.electron)throw new Error('Native network transport was not configured');return https.request(url,options,callback);}
module.exports={request,configureNodeTransport,configureElectronTransport,createElectronRequest,classifyNetworkError,networkFailure,RETRYABLE};
