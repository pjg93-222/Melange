'use strict';
// One user intent may arrive from the menu and settings at the same time.
// Share completion; never start a second backend while the first launch awaits.
function singleLaunch(action){
 let pending=null;
 const launch=function(...args){
  if(pending)return pending;
  const result=Promise.resolve().then(()=>action(...args));pending=result;
  result.finally(()=>{if(pending===result)pending=null;}).catch(()=>{});
  return result;
 };
 launch.whenIdle=()=>pending||Promise.resolve();
 return launch;
}
module.exports={singleLaunch};
