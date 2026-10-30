'use strict';
// GitHub hosts public artifacts; the independently pinned manifest signature and
// native publisher identity remain the authorities for installing them.
const network=require('./network-transport.cjs'),semver=require('semver');
const {downloadBinary}=require('./binary-download.cjs');
const {DiscoveryCache,rateLimit}=require('./github-discovery.cjs');
const PURPOSE='melange-desktop-github-release',DISTRIBUTION='public-installations';
const responseFailures=new WeakSet();
function responseIntegrity(message,cause){const error=new Error(message,{cause});responseFailures.add(error);return error;}
function isResponseIntegrity(error){return Boolean(error&&typeof error==='object'&&responseFailures.has(error));}
const ASSET_HOSTS=new Set(['github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','github-releases.githubusercontent.com']);
function repository(value){if(typeof value!=='string'||! /^[A-Za-z0-9][A-Za-z0-9_.-]*\/[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(value)||value.split('/').some(part=>part.length>100))throw new Error('Invalid GitHub repository');return value.toLowerCase();}
function configuration(value){if(!value||Object.keys(value).sort().join('|')!=='provider|repository'||value.provider!=='github')throw new Error('Invalid GitHub update configuration');return {provider:'github',repository:repository(value.repository)};}
function tag(version){if(typeof version!=='string'||!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version)||semver.valid(version)!==version)throw new Error('Stable desktop version required');return 'desktop-v'+version;}
function checkedURL(value,asset=false,cdn=false){const u=new URL(value),refresh=!u.search||/^\?refresh=(?:0|[1-9][0-9]{0,11})$/.test(u.search);const raw=cdn&&u.hostname==='raw.githubusercontent.com'&&refresh&&/^\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/main\/docs\/(?:desktop-data\/(?:on-demand-)?current\.json|district-testsets\/current\.json)$/.test(u.pathname);const latest=u.hostname==='github.com'&&/\/releases\/latest\/download\/(?:melange|mentat|terrier)-win32-x64\.manifest\.json$/.test(u.pathname);if(u.protocol!=='https:'||u.port||u.username||u.password||u.hash||latest&&!refresh||!(cdn?raw:asset?ASSET_HOSTS.has(u.hostname):u.hostname==='api.github.com'))throw new Error('GitHub update URL refused');return u;}
function response(url,{asset=false,cdn=false,apiRaw=false,redirects=0,deadlineMs=60000,deadlineAt=Date.now()+deadlineMs,signal,range}={}){
 if(range&&(!asset||Object.keys(range).sort().join('|')!=='offset|totalBytes'||!Number.isSafeInteger(range.offset)||!Number.isSafeInteger(range.totalBytes)||range.offset<0||range.offset>=range.totalBytes||range.totalBytes>20*1024**3))throw new Error('Invalid signed binary range');
 const target=checkedURL(url,asset,cdn);
 if(apiRaw&&(asset||cdn||target.hostname!=='api.github.com'||!/^\/repos\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/contents\/docs\/(?:desktop-data\/(?:on-demand-)?current\.json|district-testsets\/current\.json|desktop-workspace\/current\.json)$/.test(target.pathname)||target.search!==(target.pathname.endsWith('/desktop-workspace/current.json')?'?ref=desktop-workspace-data':'?ref=main')))throw new Error('GitHub raw pointer API route refused');
 return new Promise((resolve,reject)=>{
  let stream;const abort=()=>{const error=Object.assign(new Error('GitHub request cancelled'),{reason:'cancelled'});request.destroy(error);};
  const clean=()=>{clearTimeout(deadline);signal?.removeEventListener('abort',abort);};
  const request=network.request(target,{method:'GET',rejectUnauthorized:true,headers:{Accept:apiRaw?'application/vnd.github.raw+json':asset?'application/octet-stream':'application/vnd.github+json','User-Agent':'MelangeDesktopUpdater/1','X-GitHub-Api-Version':'2022-11-28','Cache-Control':'no-cache','Accept-Encoding':'identity',...(range?.offset?{Range:'bytes='+range.offset+'-'}:{})}},res=>{
   stream=res;
   if(res.statusCode>=300&&res.statusCode<400){res.resume();clean();if(!asset||redirects>=3||typeof res.headers.location!=='string'||res.headers.location.length>8192){reject(responseIntegrity('GitHub redirect refused'));return;}
    let next;try{next=checkedURL(new URL(res.headers.location,target).href,true);}catch(error){reject(responseIntegrity('GitHub redirect destination refused',error));return;}
    response(next.href,{asset:true,redirects:redirects+1,deadlineMs,deadlineAt,signal,range}).then(resolve,reject);return;
   }
   if(res.headers['content-encoding']!==undefined&&res.headers['content-encoding']!=='identity'){res.destroy();clean();reject(responseIntegrity('Encoded GitHub response refused'));return;}
   if(res.statusCode!==(range?.offset?206:200)){
    const refused=body=>{clean();const limited=rateLimit(res.statusCode,res.headers,body);reject(limited?Object.assign(network.networkFailure('rate_limited','GitHub API rate limit reached'),limited):res.statusCode===407?network.networkFailure('proxy','The configured proxy requires authentication.'):[500,502,503,504].includes(res.statusCode)?network.networkFailure('unreachable','GitHub release is temporarily unavailable',{retryAfterMs:5000}):responseIntegrity('GitHub release unavailable ('+res.statusCode+')'));};
    if(res.statusCode===403){let body='';res.on('data',chunk=>{if(body.length<8192)body+=chunk.toString('utf8').slice(0,8192-body.length);});res.once('end',()=>refused(body));res.once('error',()=>refused(body));}
    else{res.resume();refused('');}return;
   }
   if(range&&(res.headers['content-length']!==String(range.totalBytes-range.offset)||res.headers['transfer-encoding']!==undefined||range.offset&&res.headers['content-range']!==`bytes ${range.offset}-${range.totalBytes-1}/${range.totalBytes}`||!range.offset&&res.headers['content-range']!==undefined)){res.destroy();clean();reject(responseIntegrity('Binary response range or signed size differs'));return;}
   res.once('end',clean);res.once('close',clean);res.once('error',clean);resolve(res);
  });
  const deadline=setTimeout(()=>request.destroy(network.networkFailure('timeout','GitHub request deadline exceeded')),Math.max(1,deadlineAt-Date.now()));
  request.setTimeout(30000,()=>request.destroy(network.networkFailure('timeout','GitHub request timed out')));
  request.once('error',error=>{clean();const classified=network.classifyNetworkError(error);if(stream&&!stream.destroyed)stream.destroy(classified);reject(classified);});signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted){abort();return;}request.end();
 });
}
async function json(url,{asset=false,cdn=false,apiRaw=false,maxBytes=2*1024*1024,signal}={}){const stream=await response(url,{asset,cdn,apiRaw,signal});const chunks=[];let size=0;for await(const chunk of stream){size+=chunk.length;if(size>maxBytes){stream.destroy();throw responseIntegrity('GitHub metadata exceeds limit');}chunks.push(chunk);}try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch(error){if(error instanceof SyntaxError)throw responseIntegrity('GitHub metadata JSON is invalid',error);throw error;}}
function fixedAssetURL(repo,version,name){return 'https://github.com/'+repository(repo)+'/releases/download/'+tag(version)+'/'+encodeURIComponent(name);}
function latestManifestURL(repo,appId,minute){if(!['melange','mentat','terrier'].includes(appId)||minute!==undefined&&(!Number.isSafeInteger(minute)||minute<0||minute>999999999999))throw new Error('Invalid GitHub latest manifest target');return 'https://github.com/'+repository(repo)+'/releases/latest/download/'+appId+'-win32-x64.manifest.json'+(minute===undefined?'':'?refresh='+minute);}
function assetURL(repo,release,name){
 const expected='https://github.com/'+repository(repo)+'/releases/download/'+tag(release.version)+'/'+encodeURIComponent(name);
 const found=release.assets.filter(item=>item&&item.name===name);
 // GitHub may return canonical owner/repository capitalization. Only these two
 // path segments are case insensitive; release tag and asset name remain exact.
 const actual=found[0]?.browser_download_url;
 const normalized=typeof actual==='string'?actual.replace(/^https:\/\/github\.com\/([^/]+)\/([^/]+)\//,(_prefix,owner,name)=>'https://github.com/'+owner.toLowerCase()+'/'+name.toLowerCase()+'/'):null;
 if(found.length!==1||normalized!==expected||!Number.isSafeInteger(found[0].size)||found[0].size<1)throw new Error('Required GitHub release asset is missing or ambiguous');
 return expected;
}
function release(value){if(!value||value.draft!==false||value.prerelease!==false||typeof value.tag_name!=='string'||!value.tag_name.startsWith('desktop-v')||!Array.isArray(value.assets)||value.assets.length>100)throw new Error('Unsupported GitHub release');const version=value.tag_name.slice(9);tag(version);return {version,assets:value.assets};}
function discoveryMetadata(values,repo){
 if(!Array.isArray(values)||values.length>500)throw new Error('Invalid cached GitHub releases');
 return values.map(item=>{
  if(item?.kind==='signed-manifest-pointer'){
   if(Object.keys(item).sort().join('|')!=='appId|kind|package|version'||!['melange','mentat','terrier'].includes(item.appId)||!item.package||Object.keys(item.package).sort().join('|')!=='name|size')throw new Error('Invalid cached signed manifest pointer');tag(item.version);
   if(item.package.name!==item.appId+'-'+item.version+'-win32-x64.exe'||!Number.isSafeInteger(item.package.size)||item.package.size<1||item.package.size>20*1024**3)throw new Error('Invalid cached signed package descriptor');
   return {kind:item.kind,appId:item.appId,version:item.version,package:{...item.package}};
  }
  if(!item||typeof item!=='object'||Object.keys(item).sort().join('|')!=='assets|version'||!Array.isArray(item.assets)||item.assets.length>9)throw new Error('Invalid cached GitHub release');tag(item.version);
  const names=new Set();const assets=item.assets.map(asset=>{
   if(!asset||Object.keys(asset).sort().join('|')!=='browser_download_url|name|size'||typeof asset.browser_download_url!=='string'||asset.browser_download_url.length>1024||!['melange','mentat','terrier'].some(app=>[app+'-win32-x64.manifest.json',app+'-trust.json',app+'-'+item.version+'-win32-x64.exe'].includes(asset.name))||names.has(asset.name))throw new Error('Invalid cached GitHub asset');
   assetURL(repo,{version:item.version,assets:[asset]},asset.name);if(asset.size>20*1024**3)throw new Error('Invalid cached GitHub asset size');names.add(asset.name);return {...asset};
  });return {version:item.version,assets};
 });
}
function githubPolicy(manifest,repo){
 if(manifest.purpose!==PURPOSE||manifest.distribution!==DISTRIBUTION||manifest.repository!==repository(repo)||manifest.platform!=='win32'||manifest.arch!=='x64'||manifest.package?.name!==manifest.appId+'-'+manifest.version+'-win32-x64.exe')throw new Error('Signed GitHub release policy does not match this installation');
 const sources=manifest.sourceRefs;
 if(!sources||Array.isArray(sources)||Object.keys(sources).sort().join('|')!=='melange|mentat|terrier')throw new Error('Signed GitHub source provenance is missing');
 for(const source of Object.values(sources)){
  if(!source||Array.isArray(source)||Object.keys(source).sort().join('|')!=='commit|ref|repository'||typeof source.ref!=='string'||source.ref.length<1||source.ref.length>512||/[\x00-\x1f\x7f]/.test(source.ref)||typeof source.commit!=='string'||!/^[0-9a-f]{40}$/.test(source.commit)||/^0{40}$/.test(source.commit))throw new Error('Invalid signed GitHub source provenance');
  repository(source.repository);
 }
 tag(manifest.version);return manifest;
}
function pointerRelease(envelope,repo,appId){
 if(!envelope||Object.keys(envelope).sort().join('|')!=='keyId|payload|schemaVersion|signature'||envelope.schemaVersion!==1||typeof envelope.keyId!=='string'||!/^[A-Za-z0-9._-]{1,100}$/.test(envelope.keyId)||typeof envelope.payload!=='string'||envelope.payload.length>1024*1024||typeof envelope.signature!=='string'||Buffer.from(envelope.signature,'base64').length!==64||Buffer.from(envelope.signature,'base64').toString('base64')!==envelope.signature)throw new Error('Invalid signed GitHub release pointer');
 const payload=Buffer.from(envelope.payload,'base64');if(payload.toString('base64')!==envelope.payload)throw new Error('Invalid signed GitHub release pointer encoding');
 // Selection is unprivileged; DesktopUpdater verifies this envelope with its
 // protected keys/high-water before downloading or native staging anything.
 const body=githubPolicy(JSON.parse(payload.toString('utf8')),repo);
 if(body.appId!==appId||!Number.isSafeInteger(body.package.size)||body.package.size<1||body.package.size>20*1024**3)throw new Error('GitHub release pointer target differs');
 return {kind:'signed-manifest-pointer',appId,version:body.version,package:{name:body.package.name,size:body.package.size}};
}
class GitHubSource{
 constructor({repository:repo,appId,platform='win32',arch='x64',readJSON=json,open=response,cacheDirectory,cacheOptions={}}){if(!['melange','mentat','terrier'].includes(appId)||platform!=='win32'||arch!=='x64')throw new Error('Unsupported GitHub desktop target');this.repository=repository(repo);this.appId=appId;this.platform=platform;this.arch=arch;this.open=open;
  this.clock=cacheOptions.now||Date.now;
  this.cache=cacheDirectory?new DiscoveryCache({...cacheOptions,cooldownScope:'api',directory:cacheDirectory,repository:this.repository,validate:values=>discoveryMetadata(values,this.repository),onStatus:value=>{this.discoveryInfo=value;}}):null;
  this.readJSON=(url,options)=>this.cache&&new URL(url).hostname==='api.github.com'?this.cache.request(()=>readJSON(url,options)):readJSON(url,options);
 }
 discoverySummary(){const info=this.discoveryInfo;if(!info)return '';if(info.backoffUntil)return 'GitHub API retry after '+new Date(info.backoffUntil).toISOString()+'.';if(!info.checkedAt)return '';return (info.cached?'Using cached release list checked ':'Release list checked ')+new Date(info.checkedAt).toISOString()+'. '+(info.refreshDeferred?'Refresh deferred.':'Next discovery after '+new Date(info.nextCheckAt).toISOString()+'.');}
 identity(enrollment){if(enrollment?.source!=='github'||enrollment.repository!==this.repository||enrollment.appId!==this.appId||enrollment.deviceToken)throw new Error('GitHub update source identity mismatch');}
 api(suffix){return 'https://api.github.com/repos/'+this.repository+'/releases'+suffix;}
 async discover(){
  const candidates=[];
  for(let page=1;page<=5;page++){
   const values=await this.readJSON(this.api('?per_page=100&page='+page));
   if(!Array.isArray(values)||values.length>100)throw responseIntegrity('Invalid GitHub releases');
   for(const value of values){
    if(value?.draft!==false||value?.prerelease!==false||typeof value.tag_name!=='string'||!value.tag_name.startsWith('desktop-v'))continue;
    const item=release(value);
    item.assets=item.assets.filter(asset=>asset&&['melange','mentat','terrier'].some(app=>[app+'-win32-x64.manifest.json',app+'-trust.json',app+'-'+item.version+'-win32-x64.exe'].includes(asset.name))).map(({name,size,browser_download_url})=>({name,size,browser_download_url}));
    candidates.push(...discoveryMetadata([item],this.repository));
   }
   if(values.length<100)break;
  }
  return candidates;
 }
 async latest({forceRefresh=false}={}){const values=this.cache?await this.cache.get(()=>this.discover({forceRefresh}),{forceRefresh}):await this.discover({forceRefresh});const candidates=values.filter(item=>{if(item.kind==='signed-manifest-pointer')return item.appId===this.appId;try{assetURL(this.repository,item,this.appId+'-'+this.platform+'-'+this.arch+'.manifest.json');return true;}catch{return false;}});return candidates.sort((a,b)=>semver.rcompare(a.version,b.version))[0]||null;}
 async refreshDiscovery(){
  this.manualDiscovery=null;
  const item=await this.latest({forceRefresh:true});
  // A failed explicit refresh must not proceed to the ordinary cached check
  // and erase the failure status with a misleading "no newer release" result.
  if(this.discoveryInfo?.backoffUntil||this.discoveryInfo?.refreshDeferred)throw new Error('GitHub release refresh deferred. '+this.discoverySummary());
  // The immediately following trust/update exchange consumes this same list,
  // including an empty result, without replacing fresh status with a cache hit.
  this.manualDiscovery={item,info:this.discoveryInfo,expiresAt:Date.now()+60000};
  return item;
 }
 async manifest(item){const name=this.appId+'-'+this.platform+'-'+this.arch+'.manifest.json',url=item.kind==='signed-manifest-pointer'?fixedAssetURL(this.repository,item.version,name):assetURL(this.repository,item,name);const envelope=await this.readJSON(url,{asset:true,maxBytes:1024*1024});if(!envelope||typeof envelope.payload!=='string'||envelope.payload.length>2*1024*1024)throw new Error('Invalid GitHub manifest');const body=githubPolicy(JSON.parse(Buffer.from(envelope.payload,'base64').toString('utf8')),this.repository);if(body.version!==item.version||body.appId!==this.appId||body.platform!==this.platform||body.arch!==this.arch)throw new Error('GitHub release target differs from signed manifest');if(item.kind==='signed-manifest-pointer'){if(item.appId!==this.appId||item.package.name!==body.package.name||item.package.size!==body.package.size)throw new Error('Signed manifest pointer package differs');}else{assetURL(this.repository,item,body.package.name);const metadata=item.assets.find(asset=>asset.name===body.package.name);if(metadata.size!==body.package.size)throw new Error('GitHub package size differs from signed manifest');}return envelope;}
 async request(enrollment,relative){
  this.identity(enrollment);const base='/v1/apps/'+this.appId;
  if(relative==='/v1/status')return {ok:true,localOnly:true};
  if(relative===base+'/trust'){const manual=this.manualDiscovery;this.manualDiscovery=null;if(manual&&Date.now()<manual.expiresAt){this.current=manual.item;this.discoveryInfo=manual.info;}else this.current=await this.latest();this.discoveryLoaded=true;if(!this.current)return {transitions:[]};const name=this.appId+'-trust.json',url=this.current.kind==='signed-manifest-pointer'?fixedAssetURL(this.repository,this.current.version,name):assetURL(this.repository,this.current,name);const result=await this.readJSON(url,{asset:true,maxBytes:1024*1024});if(!result||Object.keys(result).join('|')!=='transitions'||!Array.isArray(result.transitions)||result.transitions.length>32)throw new Error('Invalid GitHub key transitions');return result;}
  const parsed=new URL(relative,'https://local.invalid');
  if(parsed.pathname!==base+'/updates'&&parsed.pathname!==base+'/recovery')throw new Error('Unsupported GitHub update operation');
  const query=parsed.searchParams;if(query.get('platform')!==this.platform||query.get('arch')!==this.arch)throw new Error('GitHub release target mismatch');
  if(parsed.pathname.endsWith('/recovery')){const expected=tag(query.get('version')),item=release(await this.readJSON(this.api('/tags/'+expected)));if(tag(item.version)!==expected)throw new Error('Recovery release tag mismatch');return this.manifest(item);}
  const item=this.discoveryLoaded?this.current:await this.latest();
  if(this.discoveryInfo?.refreshDeferred||this.discoveryInfo?.backoffUntil)throw network.networkFailure(this.discoveryInfo.backoffUntil?'rate_limited':'unreachable','Current GitHub update status is unavailable; the last release information could not be refreshed.',{retryAfterMs:this.discoveryInfo.backoffUntil?this.discoveryInfo.backoffUntil-this.clock():5000});
  if(!item||semver.lte(item.version,query.get('version')))return null;return this.manifest(item);
 }
 async download(enrollment,_token,manifest,directory,{manifestHash,signal,onProgress}={}){
  this.identity(enrollment);githubPolicy(manifest,this.repository);
  if(manifest.appId!==this.appId)throw new Error('GitHub package belongs to another app');
  const url=fixedAssetURL(this.repository,manifest.version,manifest.package.name);
  return downloadBinary({url,directory,manifest,manifestHash,signal,onProgress,open:this.open});
 }
}
async function enrollGitHub({appId,publicKeys,config,load,save}){
 const selected=configuration(config);
 if(!['melange','mentat','terrier'].includes(appId)||!publicKeys||Array.isArray(publicKeys)||Object.keys(publicKeys).length<1||Object.keys(publicKeys).length>8)throw new Error('Packaged GitHub verification keys are required');
 for(const [id,key] of Object.entries(publicKeys))if(!/^[A-Za-z0-9._-]{1,100}$/.test(id)||typeof key!=='string'||Buffer.from(key,'base64').length!==32||Buffer.from(key,'base64').toString('base64')!==key)throw new Error('Invalid packaged GitHub verification key');
 const previous=await load();if(previous){if(previous.source!=='github'||previous.repository!==selected.repository||previous.appId!==appId||previous.deviceToken||Object.entries(publicKeys).some(([id,key])=>previous.publicKeys?.[id]!==key))throw new Error('Protected GitHub source differs from the packaged verification identity');return previous;}
 // Public binary updates are independent of app login/approval. No access token,
 // account state or device identifier is needed or sent to GitHub.
 const value={source:'github',repository:selected.repository,appId,publicKeys:structuredClone(publicKeys)};await save(value);return value;
}
module.exports={GitHubSource,configuration,repository,tag,checkedURL,githubPolicy,enrollGitHub,response,json,assetURL,release,discoveryMetadata,pointerRelease,fixedAssetURL,latestManifestURL,isResponseIntegrity};
