'use strict';
const byId=id=>document.getElementById(id);
const status=message=>{byId('status').textContent=message;};
async function action(fn){try{await fn();}catch(error){status(error.message);}}
function showAuthentication(info){
 const windows=info.authentication==='windows',label=byId('authentication'),account=byId('windows-account'),name=info.windowsAccountDisplayName;
 label.hidden=!windows;label.textContent=windows?'Uses your current Windows sign-in. No separate application password.':'';
 const valid=windows&&typeof name==='string'&&name.trim()===name&&Array.from(name).length>0&&Array.from(name).length<=256&&!/[\x00-\x1f\x7f]/.test(name);
 account.hidden=!valid;account.textContent=valid?'Windows account: '+name:'';
}
async function refresh(){const info=await window.desktop.info();document.title=info.name+' settings';byId('name').textContent=info.name;if(['melange','terrier','mentat'].includes(info.appId)){byId('app-logo').src='icons/'+info.appId+'.ico';byId('app-logo').hidden=false;document.body.dataset.app=info.appId;}showAuthentication(info);byId('pairing').hidden=info.updateProvider==='github';byId('pair').hidden=info.updateProvider==='github';byId('paired').textContent=info.updateProvider==='github'?(info.paired?'GitHub update receiver is ready for signed releases.':'GitHub update receiver is being initialized.'):(info.paired?'Paired with administrator.':'Not paired.');status(info.status);}
byId('launch').addEventListener('click',()=>action(()=>window.desktop.launch()));
byId('pair').addEventListener('click',()=>action(async()=>{await window.desktop.pair(byId('pairing').value);byId('pairing').value='';await refresh();}));
window.desktop.onStatus(status);action(refresh);
const disposeUpdates=window.desktopUpdateStatus?.mount(document,window.desktop,{onInfo:info=>{
 const github=info.provider==='github';byId('update-heading').textContent=github?'GitHub updates':'Publisher updates';
 byId('update-description').textContent=github?'Signed GitHub releases download automatically and install after you close the app. Your local data is retained.':'This installation receives signed releases from its configured publisher. Pairing is needed only when that publisher supplies a bundle.';
 if(info.accessMode==='standalone')byId('settings-description').textContent='Local application and GitHub release updates.';
 byId('pairing').hidden=github;byId('pair').hidden=github;
}});
window.addEventListener('pagehide',()=>disposeUpdates?.(),{once:true});
