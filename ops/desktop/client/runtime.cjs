'use strict';
const {spawn}=require('node:child_process');
const net=require('node:net');
const http=require('node:http');
const crypto=require('node:crypto');
const fs=require('node:fs');
const path=require('node:path');
const {appDefinition}=require('./apps.cjs');
const {backendCommand,backendEnvironment}=require('./backend-command.cjs');
const {runtimeRoots,prepareRuntimeRoots,validatedLaunchPath,refuseInstalledOverlap}=require('./runtime-roots.cjs');
const {initializeModuleRuntime,consumeModuleCapability,activeModule,setActiveModule,clearActiveModule,matchesModuleHealth,checkWarmModule,writeModuleFrame,verifyProgramPair}=require('./module-data-runtime-boundary.cjs');
const {observeStartupData}=require('./startup-data-diagnostic.cjs');
// One value per app process, never written anywhere: Terrier's approved owner session is bound to this native launch.
const OWNER_SESSION_KEY=crypto.randomBytes(32).toString('base64url');
// A consumed launch capability cannot be replayed. Only its already accepted,
// still-running native child may retain authority across Windows sleep/unlock.
const ACTIVE_DISTRICTS=new WeakMap();
const canonical=require('./access-client.cjs').canonical;
function districtPaths(runtime){
  const source=path.join(backendCommand(runtime.resources,'terrier').runtime,'sources');
  return canonical({profileRoot:fs.realpathSync.native(runtime.userData),sourceRoot:fs.realpathSync.native(source),
    dataRoot:fs.realpathSync.native(runtime.roots.data),stateRoot:fs.realpathSync.native(runtime.roots.state)});
}
function rememberDistrict(runtime,configuration,ready){
  if(!runtime.child||childExited(runtime.child)||ready.pid!==runtime.child.pid)throw require('./startup-failure.cjs').programFailure();
  ACTIVE_DISTRICTS.set(runtime,{child:runtime.child,generation:runtime.generation||0,configuration:canonical(configuration),
    roots:canonical(runtime.roots),paths:districtPaths(runtime),origin:runtime.origin,token:runtime.token,
    authorization:require('./access-lifecycle.cjs').authorizationIdentity(runtime.authorization),
    health:canonical({pid:ready.pid,districtData:ready.districtData}),programFingerprint:ready.districtData.programFingerprint});
}
function warmDistrict(runtime,configuration){
  const record=ACTIVE_DISTRICTS.get(runtime);
  if(!record||record.child!==runtime.child||childExited(runtime.child)||record.generation!==(runtime.generation||0)||
    record.configuration!==canonical(configuration)||record.configuration!==canonical(runtime.configuration)||
    record.roots!==canonical(runtime.roots)||record.origin!==runtime.origin||record.token!==runtime.token)return null;
  return record;
}
function checkDistrict(runtime,configuration,record,ready){
  try{
    if(warmDistrict(runtime,configuration)!==record||record.paths!==districtPaths(runtime)||
      record.authorization!==require('./access-lifecycle.cjs').authorizationIdentity(runtime.authorization)||
      require('./district-data-probe.cjs').verifyDistrictProgram(runtime).programFingerprint!==record.programFingerprint||
      (ready!==undefined&&(!ready||record.health!==canonical({pid:ready.pid,districtData:ready.districtData}))))throw new Error();
  }catch{throw require('./startup-failure.cjs').programFailure();}
}

function freePort(){return new Promise((resolve,reject)=>{const s=net.createServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const port=s.address().port;s.close(()=>resolve(port));});});}
// Native health verifies both installed data bindings; a valid response can exceed one second on a busy Windows host.
const HEALTH_REQUEST_TIMEOUT_MS=5000;
function health(origin,token,appId){return new Promise(resolve=>{const request=http.get(origin+'/__desktop/health',{headers:{'X-Desktop-Token':token},timeout:HEALTH_REQUEST_TIMEOUT_MS},response=>{let body='';response.on('data',c=>{body+=c;if(body.length>4096)response.destroy();});response.on('error',()=>resolve(null));response.on('close',()=>resolve(null));response.on('end',()=>{try{const value=JSON.parse(body);if(response.statusCode!==200||value.appId!==appId){resolve(null);return;}resolve({launchPath:validatedLaunchPath(appId,value.launchPath),...(Object.hasOwn(value,'moduleData')?{appId:value.appId,pid:value.pid,moduleData:value.moduleData}:{}),...(Object.hasOwn(value,'workspaceData')?{workspaceData:value.workspaceData}:{}),...(Object.hasOwn(value,'districtData')?{appId:value.appId,pid:value.pid,districtData:value.districtData}:{})});}catch{resolve(null);}});});request.on('timeout',()=>request.destroy());request.on('error',()=>resolve(null));});}
async function probe(origin,token,appId){return Boolean(await health(origin,token,appId));}
function activity(origin,token,appId){return new Promise(resolve=>{
  if(!origin||!token){resolve(null);return;}
  const request=http.get(origin+'/__desktop/activity',{headers:{'X-Desktop-Token':token},timeout:1000},response=>{
    let body='';response.on('data',chunk=>{body+=chunk;if(body.length>4096)response.destroy();});
    response.on('error',()=>resolve(null));response.on('close',()=>resolve(null));
    response.on('end',()=>{try{const value=JSON.parse(body);resolve(response.statusCode===200&&value.appId===appId&&typeof value.busy==='boolean'?value.busy:null);}catch{resolve(null);}});
  });request.on('timeout',()=>request.destroy());request.on('error',()=>resolve(null));
});}
function refuseModuleDataSettings(configuration){
  // Settings cannot turn their source descriptor into a native launch capability.
  if(configuration!==null&&configuration!==undefined&&['ownerGitHubModuleData','ownerGitHubWorkspaceData'].some(key=>Object.hasOwn(configuration,key)))throw new Error('GitHub module data startup is unavailable in this build.');
}
const childExited=child=>Boolean(child&&(child.exitCode!=null||child.signalCode!=null));
function waitForChildExit(child,timeout){
  if(childExited(child))return Promise.resolve(true);
  return new Promise(resolve=>{
    let timer;const done=()=>{clearTimeout(timer);child.removeListener('exit',done);resolve(childExited(child));};
    child.once('exit',done);timer=setTimeout(done,timeout);if(childExited(child))done();
  });
}
function requestWindowsStop(child){
  return new Promise(resolve=>{
    let killer,timer,finished=false;
    const done=()=>{if(finished)return;finished=true;clearTimeout(timer);resolve();};
    const fallback=()=>{try{child.kill();}catch{}done();};
    try{killer=spawn('taskkill.exe',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}catch{fallback();return;}
    killer.once('error',fallback);killer.once('exit',done);
    timer=setTimeout(()=>{try{killer.kill('SIGKILL');}catch{}done();},5000);
    if(childExited(killer))done();
  });
}
class Runtime {
  constructor(appId,userData,resources,{protectedPaths=[],rendererFactory=null,scrapeFactory=null,authorize=null,allowStandalone=false,authentication='password',confine=null,logRoot=null,districtInputRequired=false}={}){this.districtInputRequired=districtInputRequired===true;this.allowStandalone=allowStandalone===true;if(!['windows','password'].includes(authentication)||(authentication==='windows'&&!this.allowStandalone))throw new Error('Unsupported runtime authentication mode');this.authentication=authentication;this.logRoot=logRoot;this.definition=appDefinition(appId);this.userData=userData;this.resources=resources;this.protectedPaths=protectedPaths;this.rendererFactory=rendererFactory;this.scrapeFactory=scrapeFactory;this.scrape=null;this.authorize=authorize;this.confine=confine;this.authorization=null;this.renderer=null;this.child=null;this.origin=null;this.token=null;this.launchPath='/';this.roots=null;this.configuration=null;
    initializeModuleRuntime(this,()=>{const command=backendCommand(this.resources,this.definition.id);return {source:path.join(command.runtime,'sources'),bootstrap:path.join(command.runtime,'bootstrap')};});}
  async start(configuration,capability){
    const districtInput=this.definition.id==='terrier'?require('./district-runtime-input.cjs').consumeDistrictConfiguration(this,configuration):null;
    try{
    const retainedDistrict=!districtInput?warmDistrict(this,configuration):null;
    if(this.districtInputRequired&&(configuration.standaloneGitHubData||configuration.terrierGitHubData)&&!districtInput&&!retainedDistrict)throw require('./startup-failure.cjs').programFailure();
    if(districtInput)await districtInput.validate();
    if(this.stopPromise||(this.stoppingChild&&!childExited(this.stoppingChild)))throw new Error('Application shutdown is still pending.');
    if(this.stoppingChild){if(this.child===this.stoppingChild)this.child=null;this.stoppingChild=null;}
    refuseModuleDataSettings(configuration);
    configuration=structuredClone(configuration);
    const moduleInput=capability===undefined?null:consumeModuleCapability(this,capability,configuration);
    const generation=this.generation||0,check=()=>{if(generation!==(this.generation||0))throw new Error('Application startup cancelled.');moduleInput?.guard();};
    if(moduleInput){await moduleInput.validate();check();}
    if(typeof this.authorize!=='function')throw new Error('Local authentication is required.');
    const authorization=await this.authorize(configuration);
    check();
    moduleInput?.checkAuthorization(authorization);
    if(authorization?.mode==='standalone'){
      if(!this.allowStandalone||authorization.identity?.appId!==this.definition.id)throw new Error('Local authorization is unavailable in this build.');
      require('./access-lifecycle.cjs').authorizationIdentity(authorization);
      if((authorization.session?.method==='windows-session')!==(this.authentication==='windows'))throw new Error('The local sign-in does not match this build.');
    }else if(!authorization?.accepted?.grant||authorization.accepted.revoked)throw new Error('Administrator approval is required.');
    if(this.child&&this.authorization&&require('./access-lifecycle.cjs').authorizationIdentity(authorization)!==require('./access-lifecycle.cjs').authorizationIdentity(this.authorization))throw new Error('Close the app before changing its approved account.');
    this.authorization=authorization;
    const desired=runtimeRoots(this.definition.id,this.userData,configuration);
    if(desired.standaloneDistrictData&&!this.allowStandalone)throw new Error('Local district data is unavailable in this build.');
    if(desired.standaloneDistrictData&&authorization.mode!=='standalone')throw new Error('Local district authorization is required.');
    if(this.child){if(JSON.stringify(desired)!==JSON.stringify(this.roots))throw new Error('Close the app before changing its district or data directory.');
      if(districtInput){const child=this.child,ready=await health(this.origin,this.token,this.definition.id);check();if(this.child!==child||!districtInput.matchesWarm(ready,this.roots))throw require('./startup-failure.cjs').programFailure();await districtInput.commit();check();rememberDistrict(this,configuration,ready);}
      else if(retainedDistrict){checkDistrict(this,configuration,retainedDistrict);const ready=await health(this.origin,this.token,this.definition.id);check();checkDistrict(this,configuration,retainedDistrict,ready);}
      checkWarmModule(this,configuration,authorization);
      if(activeModule(this)){const child=this.child,ready=await health(this.origin,this.token,this.definition.id);check();if(this.child!==child||!matchesModuleHealth(this,ready))throw new Error('Native module input is unavailable.');}
      this.configuration=configuration;return this.origin;}
    // Isolated test profiles only: every backend root must stay inside the isolated tree,
    // checked before any directory is created and again immediately before spawn.
    const confineRoots=roots=>{if(this.confine)this.confine([configuration.dataDirectory,roots.data,roots.state]);};
    confineRoots(desired);
    const appId=this.definition.id, command=backendCommand(this.resources,appId),{binary,runtime}=command;
    const roots=prepareRuntimeRoots(appId,this.userData,configuration,[this.resources,path.dirname(binary),...this.protectedPaths]);confineRoots(roots);this.roots=roots;
    const port=await freePort();check();this.token=crypto.randomBytes(32).toString('base64url');this.origin='http://127.0.0.1:'+port;
    // logRoot (Terrier's private store, main.cjs) keeps backend.log out of the synced profile; the legacy owner and the other apps log in the profile.
    const state=roots.state,logs=this.logRoot&&!roots.legacyOwner?this.logRoot:path.join(this.userData,'logs');fs.mkdirSync(logs,{recursive:true});
    const environment={...backendEnvironment(),DESKTOP_LAUNCH_TOKEN:this.token};
    if(authorization.mode==='standalone')delete environment.DESKTOP_ACCESS_PRINCIPAL;
    if(appId==='terrier'){
      if(!authorization.principal||authorization.principal.districtId!==roots.district)throw new Error('Approved Terrier account is required.');
      if(authorization.mode!=='standalone')environment.DESKTOP_ACCESS_PRINCIPAL=JSON.stringify(authorization.principal);
    }
    // The existing owner's one password and sign-in for all districts live in the profile's desktop-level state.
    const ownerRoot=roots.legacyOwner?path.join(this.userData,'state','terrier-owner'):null;
    if(ownerRoot){refuseInstalledOverlap(ownerRoot,[this.resources,path.dirname(binary),...this.protectedPaths]);environment.DESKTOP_OWNER_SESSION_KEY=OWNER_SESSION_KEY;}
    if(appId==='mentat'&&this.rendererFactory){this.renderer=await this.rendererFactory();environment.MENTAT_DESKTOP_RENDER_URL=this.renderer.url;environment.MENTAT_DESKTOP_RENDER_TOKEN=this.renderer.token;}
    // Shared collection (SCRAPE-BROKER.md): a per-launch loopback capability for this backend only. It carries neither the
    // access bearer nor any provider key, and it closes with the backend.
    try{if(['melange','mentat'].includes(appId)&&this.scrapeFactory){this.scrape=await this.scrapeFactory(configuration);environment.MELANGE_SCRAPE_BROKER_URL=this.scrape.url;environment.MELANGE_SCRAPE_BROKER_TOKEN=this.scrape.token;}}catch(error){if(this.renderer)await Promise.resolve().then(()=>this.renderer.close()).catch(()=>{});this.renderer=null;throw error;}
    const renderer=this.renderer,scrape=this.scrape;
    try{check();}catch(error){if(renderer)await Promise.resolve().then(()=>renderer.close()).catch(()=>{});if(scrape)await Promise.resolve().then(()=>scrape.close()).catch(()=>{});if(this.renderer===renderer)this.renderer=null;if(this.scrape===scrape)this.scrape=null;throw error;}
    if(this.confine){try{confineRoots(roots);this.confine(ownerRoot?[logs,ownerRoot]:[logs]);}catch(error){this.renderer=null;this.scrape=null;if(renderer)await Promise.resolve().then(()=>renderer.close()).catch(()=>{});if(scrape)await Promise.resolve().then(()=>scrape.close()).catch(()=>{});this.roots=null;this.origin=null;this.token=null;throw error;}}
    const log=fs.openSync(path.join(logs,'backend.log'),'a',0o600);
    const args=[...command.args,'--app',appId,'--port',String(port),'--source-root',path.join(runtime,'sources'),'--data-root',roots.data,'--state-root',state];
    if(appId==='terrier') args.push('--district',roots.district);
    if(appId==='terrier'&&authorization.mode==='standalone')args.push('--standalone');
    if(appId==='terrier'&&authorization.mode==='standalone'&&this.authentication==='windows')args.push('--windows-session');
    if(roots.legacyOwner) args.push('--legacy-owner',roots.legacyOwner,'--owner-root',ownerRoot);
    if(roots.githubDistrictData===true) args.push('--github-district-data');
    if(moduleInput)args.push(moduleInput.wire==='workspace'?'--desktop-workspace-input':'--desktop-module-input','--profile-root',this.userData);
    if(districtInput)args.push('--desktop-district-input','--profile-root',this.userData);
    let child;
    try{child=spawn(binary,args,{cwd:runtime,env:environment,windowsHide:true,detached:process.platform!=='win32',stdio:[moduleInput||districtInput?'pipe':'ignore',moduleInput||districtInput?'pipe':log,log]});}catch(error){if(renderer)await Promise.resolve().then(()=>renderer.close()).catch(()=>{});if(scrape)await Promise.resolve().then(()=>scrape.close()).catch(()=>{});this.renderer=null;this.scrape=null;throw error;}finally{fs.closeSync(log);}
    this.child=child;
    let intake=null;
    let failed=null;child.once('error',error=>{failed=error;});child.once('exit',(code)=>{failed=new Error('Backend stopped (exit '+code+'). See backend.log.');clearActiveModule(this,child);if(ACTIVE_DISTRICTS.get(this)?.child===child)ACTIVE_DISTRICTS.delete(this);if(this.child===child){this.child=null;this.configuration=null;}if(renderer&&this.renderer===renderer){this.renderer=null;Promise.resolve(renderer.close()).catch(()=>{});}if(scrape&&this.scrape===scrape){this.scrape=null;Promise.resolve(scrape.close()).catch(()=>{});}});
    try{
      if(moduleInput){setActiveModule(this,moduleInput,child);moduleInput.claimChild(child);check();
        intake=observeStartupData(child,{appId,launchNonce:moduleInput.launchNonce,programFingerprint:moduleInput.contract.programFingerprint,
          sourceDigests:{public:moduleInput.binding.sourceDigest,...(moduleInput.workspaceBinding?{workspace:moduleInput.workspaceBinding.sourceDigest}:{})},
          guard:()=>{moduleInput.guard();verifyProgramPair(this,moduleInput.contract,moduleInput.workspaceContract);}});
        if(child.stdout){const output=fs.createWriteStream(path.join(logs,'backend.log'),{flags:'a',mode:0o600});output.on('error',()=>{child.stdout.unpipe(output);child.stdout.resume();});child.stdout.pipe(output);}
        await writeModuleFrame(child,moduleInput.frame(roots),moduleInput.signal);check();}
      if(districtInput){
        const frame=districtInput.frame(roots,path.join(runtime,'sources'));intake=observeStartupData(child,districtInput.diagnostic());
        if(child.stdout){const output=fs.createWriteStream(path.join(logs,'backend.log'),{flags:'a',mode:0o600});output.on('error',()=>{child.stdout.unpipe(output);child.stdout.resume();});child.stdout.pipe(output);}
        await writeModuleFrame(child,frame,undefined,districtInput.maximum);check();
      }
      let districtCommitted=false;
      const deadline=Date.now()+(moduleInput?moduleInput.startupTimeoutMs:120000);
      while(Date.now()<deadline){check();if(failed)throw failed;if(this.child!==child)throw new Error('Application startup cancelled.');const ready=await health(this.origin,this.token,appId);check();if(failed)throw failed;if(this.child!==child)throw new Error('Application startup cancelled.');
        if(districtInput&&ready&&!districtCommitted&&districtInput.matches(ready,'prepared')){await districtInput.commitNative(this.origin,this.token);check();districtCommitted=true;continue;}
        if(ready&&(!moduleInput||matchesModuleHealth(this,ready))&&(!districtInput||districtInput.matches(ready,'active'))){if(districtInput){await districtInput.commit();check();rememberDistrict(this,configuration,ready);}intake?.markHealthy();this.launchPath=ready.launchPath;this.configuration=configuration;return this.origin;}await new Promise(r=>setTimeout(r,250));}
      throw new Error('Application startup timed out. See backend.log.');
    }catch(error){
      const blocked=intake&&!require('./startup-failure.cjs').isDataStartupFailure(error)?await intake.blockedAfterExit({waitForExit:Boolean(districtInput)}):null;if(blocked)throw blocked;
      // Module teardown follows the coordinator's protected provider drain.
      // Ordinary starts retain their existing immediate owned-child cleanup.
      if(!moduleInput&&this.child===child)await this.stop();
      throw error;
    }
    }catch(error){
      if(districtInput){
        require('./district-data-probe.cjs').verifyDistrictProgram(this);
        if(this.child)await this.stop();
        try{await this.authorize(configuration);}catch{const paused=new Error('The current Windows sign-in is unavailable.');paused.code=paused.reason='authorization';throw paused;}
        if(['EACCES','EPERM','ENOENT','EBUSY','ENOSPC','EDQUOT','EIO','EROFS'].includes(error?.code))throw require('./startup-failure.cjs').dataStartupFailure({reason:'storage'});
      }
      throw error;
    }finally{await districtInput?.close();}
  }
  originalConfiguration(){return this.configuration===null?null:structuredClone(this.configuration);}
  async verifyModuleHealth(binding){const active=activeModule(this),child=this.child,generation=this.generation||0,origin=this.origin,token=this.token;if(!active||active.child!==child)return false;const value=await health(origin,token,this.definition.id);return this.child===child&&(this.generation||0)===generation&&this.origin===origin&&this.token===token&&activeModule(this)===active&&matchesModuleHealth(this,value,binding);}
  stop(){
    this.requestsAllowed=false;ACTIVE_DISTRICTS.delete(this);
    if(this.stopPromise)return this.stopPromise;
    this.generation=(this.generation||0)+1;
    const child=this.stoppingChild||this.child,renderer=this.renderer,scrape=this.scrape;
    this.stoppingChild=child;clearActiveModule(this);
    this.renderer=null;this.scrape=null;this.origin=null;this.token=null;this.launchPath='/';this.roots=null;this.configuration=null;
    const operation=(async()=>{
      if(renderer)await Promise.resolve().then(()=>renderer.close()).catch(()=>{});
      if(scrape)await Promise.resolve().then(()=>scrape.close()).catch(()=>{});
      if(child&&!childExited(child)){
        if(process.platform==='win32')await requestWindowsStop(child);
        else try{process.kill(-child.pid,'SIGTERM');}catch{}
        if(!await waitForChildExit(child,5000)){
          try{if(process.platform==='win32')child.kill('SIGKILL');else process.kill(-child.pid,'SIGKILL');}catch{}
          // A signal request is not proof of exit: callers may retire its data only after this resolves.
          if(!await waitForChildExit(child,5000))throw Object.assign(new Error('Backend shutdown did not complete. Its data must be retained.'),{code:'BACKEND_STOP_TIMEOUT'});
        }
      }
      if(this.child===child)this.child=null;
      if(this.stoppingChild===child)this.stoppingChild=null;
    })();
    const pending=operation.finally(()=>{if(this.stopPromise===pending)this.stopPromise=null;});
    this.stopPromise=pending;return pending;
  }
  activity(){return activity(this.origin,this.token,this.definition.id);}
}
function suspendedAuthRequest(details,runtime){
 if(!runtime.authenticationContentsId||details.webContentsId!==runtime.authenticationContentsId)return false;
 const url=new URL(details.url);if(url.origin!==runtime.origin)return false;
 if(details.method==='GET'&&['/desktop-signin','/api/auth/session'].includes(url.pathname))return true;
 if(details.method==='POST'&&['/api/auth/login','/api/auth/accept','/api/auth/logout'].includes(url.pathname))return true;
 return details.method==='GET'&&/^\/(assets|brand)\/[^/]+\.(js|css|woff2?|png|svg|ico|webp|mp4)$/.test(url.pathname);
}
function attachLaunchHeader(session,source,knownOrigins=()=>[]){
  const current=typeof source==='function'?source:()=>source;
  const owned=(details,runtime)=>Number.isInteger(runtime.contentsId)&&details.webContentsId===runtime.contentsId;
  session.webRequest.onBeforeRequest?.((details,callback)=>{const runtime=current(),origin=new URL(details.url).origin;callback({cancel:Boolean((origin!==runtime.origin&&knownOrigins().includes(origin))||(runtime.origin&&origin===runtime.origin&&!((owned(details,runtime)&&runtime.requestsAllowed!==false)||suspendedAuthRequest(details,runtime))))});});
  session.webRequest.onBeforeSendHeaders((details,callback)=>{
    const runtime=current();
    const headers={...details.requestHeaders};for(const key of Object.keys(headers))if(key.toLowerCase()==='x-desktop-token')delete headers[key];
    if(((owned(details,runtime)&&runtime.requestsAllowed!==false)||suspendedAuthRequest(details,runtime))&&runtime.origin&&new URL(details.url).origin===runtime.origin) headers['X-Desktop-Token']=runtime.token;
    callback({requestHeaders:headers});
  });
}
module.exports={Runtime,freePort,probe,health,activity,attachLaunchHeader,suspendedAuthRequest,refuseModuleDataSettings};
