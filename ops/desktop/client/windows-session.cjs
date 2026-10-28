'use strict';
const {backendCommand}=require('./backend-command.cjs');
const {desktopProbe}=require('./desktop-probe.cjs');
function validWindowsSession(value){
 return Boolean(value&&Object.getPrototypeOf(value)===Object.prototype&&Object.keys(value).sort().join(',')==='accountName,locked,schemaVersion,sessionId,userSid'&&value.schemaVersion===1&&typeof value.userSid==='string'&&value.userSid.length<=184&&/^S-1-\d+(?:-\d+){1,15}$/.test(value.userSid)&&!['S-1-5-18','S-1-5-19','S-1-5-20'].includes(value.userSid)&&typeof value.accountName==='string'&&value.accountName.length>0&&value.accountName.length<=256&&!/[\x00-\x1f\x7f]/.test(value.accountName)&&Number.isInteger(value.sessionId)&&value.sessionId>0&&value.sessionId<0xffffffff&&typeof value.locked==='boolean');
}
async function windowsSession(resources,appId){
 if(process.platform!=='win32'||!['melange','mentat','terrier'].includes(appId))throw new Error('Windows sign-in is unavailable.');
 const value=await desktopProbe(backendCommand(resources,appId),'--desktop-windows-session',{},{timeout:15000,limit:8192});
 if(!validWindowsSession(value))throw new Error('Windows sign-in could not be verified.');
 return Object.freeze({...value});
}
module.exports={windowsSession,validWindowsSession};
