'use strict';
// Shows the main process's progress text (district download, retries, a stopped download) under the loading animation.
const detail=document.getElementById('detail');
window.desktop?.onStatus(text=>{detail.textContent=text;});
const disposeUpdates=window.desktopUpdateStatus?.mount(document,window.desktop,{onInfo:info=>{
 document.title=info.appName;document.getElementById('loading-name').textContent=info.appName;document.body.dataset.app=info.appId;
 const icon=document.getElementById('loading-icon'),video=document.getElementById('loading-video');
 icon.src=info.appId==='terrier'?'loading-assets/terrier-icon-hq.png':'icons/'+info.appId+'.ico';icon.hidden=false;
 const reduced=Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);document.body.classList.toggle('reduced-motion',reduced);
 video.hidden=info.appId!=='terrier'||reduced;
 if(!video.hidden&&!video.dataset.loaded){video.dataset.loaded='true';video.src='loading-assets/terrier-loading-hq.mp4';video.play().catch(()=>{});}
}});
window.addEventListener('pagehide',()=>disposeUpdates?.(),{once:true});
