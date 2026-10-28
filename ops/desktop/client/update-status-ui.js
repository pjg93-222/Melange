'use strict';
(function(root){
  const APPS={melange:'Melange',mentat:'Mentat',terrier:'Terrier'};
  const STATES=new Set(['waiting','checking','current','downloading','ready','unavailable']);
  function validate(value,expectedApp){
    if(!value||typeof value!=='object'||APPS[value.appId]!==value.appName||(expectedApp&&value.appId!==expectedApp)||
      typeof value.installedVersion!=='string'||value.installedVersion.length>50||!/^\d+\.\d+\.\d+$/.test(value.installedVersion)||
      !['github','publisher'].includes(value.provider)||!['standalone','managed'].includes(value.accessMode)||!STATES.has(value.state)||
      typeof value.message!=='string'||!value.message||value.message.length>200||/[\x00-\x1f\x7f]/.test(value.message))throw new Error('Invalid update status');
    return value;
  }
  function mount(document,api,{onInfo=()=>{}}={}){
    const container=document.getElementById('desktop-update-status'),version=document.getElementById('desktop-installed-version'),message=document.getElementById('desktop-update-message');
    if(!container||!version||!message)return()=>{};
    let appId=null,disposed=false,events=0,unsubscribe;
    const unavailable=()=>{if(disposed)return;container.dataset.state='unavailable';message.textContent='Update status unavailable.';};
    function render(raw){if(disposed)return;try{const info=validate(raw,appId);appId=info.appId;container.dataset.state=info.state;version.textContent=info.appName+' · Installed version '+info.installedVersion;message.textContent=(info.provider==='github'?'GitHub updates: ':'Application updates: ')+info.message;onInfo(info);}catch{unavailable();}}
    if(!api||typeof api.getUpdateInfo!=='function'||typeof api.onUpdateStatus!=='function'){unavailable();return()=>{};}
    try{unsubscribe=api.onUpdateStatus(value=>{events++;render(value);});const initialEvents=events;Promise.resolve(api.getUpdateInfo()).then(value=>{if(events===initialEvents)render(value);},()=>{if(events===initialEvents)unavailable();});}catch{unavailable();}
    return()=>{disposed=true;if(typeof unsubscribe==='function')unsubscribe();};
  }
  if(typeof module==='object'&&module.exports)module.exports={validate,mount};else root.desktopUpdateStatus=Object.freeze({mount});
})(typeof window==='object'?window:globalThis);
