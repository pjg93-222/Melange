'use strict';
const APPS=Object.freeze({melange:'Melange',mentat:'Mentat',terrier:'Terrier'});
const VERSION=/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
function createUpdateStatus({appId,appName,installedVersion,provider='github',accessMode='managed',now=()=>new Date()}={}){
  if(APPS[appId]!==appName||typeof installedVersion!=='string'||installedVersion.length>50||!VERSION.test(installedVersion)||
    !['github','publisher'].includes(provider)||!['standalone','managed'].includes(accessMode))throw new Error('Invalid update presentation identity');
  const identity={appId,appName,installedVersion,provider,accessMode};
  let snapshot=Object.freeze({...identity,state:'waiting',message:'Waiting to check for updates.',checkedAt:null});
  return Object.freeze({current:()=>snapshot,record(raw){
    const text=typeof raw==='string'?raw.slice(0,4096):'';
    let state='unavailable',message='Update status unavailable.',checkedAt=snapshot.checkedAt;
    const version=/^(?:Downloading verified update|Verified update|Update|Previous version) ([0-9]{1,10}\.[0-9]{1,10}\.[0-9]{1,10})/.exec(text)?.[1];
    const discovered=/(?:Release list checked|Using cached release list checked) (\d{4}-\d{2}-\d{2}T[\d:.]+Z)/.exec(text)?.[1];
    const checked=()=>discovered&&Number.isFinite(Date.parse(discovered))?discovered:now().toISOString();
    if(/^Checking for updates/.test(text)){state='checking';message='Checking for updates…';}
    else if(version&&/^Downloading verified update /.test(text)){state='downloading';message='Downloading version '+version+'…';}
    else if(version&&/^(?:Verified update [0-9.]+ waits for this app to close|Update [0-9.]+ verified\.)/.test(text)){state='ready';message='Version '+version+' ready; installs when you close the app.';}
    else if(version&&/^Previous version [0-9.]+ verified/.test(text)){state='ready';message='Recovery version '+version+' ready; installs when you close the app.';}
    else if(/(?:deferred|refused|failed|failure|unavailable|suspended|not initialized|initialization is pending|initialization failed|did not complete|GitHub API retry after)/i.test(text)){
      message=/verified update remains staged/i.test(text)?'Update check unavailable; a verified update is still staged.':'Update check unavailable. It will retry automatically.';
    }else if(/awaits a successful local startup/.test(text)){
      state='waiting';message=/^No newer signed update\./.test(text)?'No newer release; local startup is not yet confirmed.':'Local startup is not yet confirmed; updates can still be checked.';
      if(/^No newer signed update\./.test(text))checkedAt=checked();
    }else if(/^(?:Already current\.|No newer signed update\.|No approved update\.)/.test(text)){
      state='current';message=/Using cached release list checked/.test(text)?'No newer release in the last checked release list.':'Up to date with published releases.';checkedAt=checked();
    }
    snapshot=Object.freeze({...identity,state,message,checkedAt});return snapshot;
  }});
}
module.exports={createUpdateStatus};
