'use strict';
const fs=require('node:fs'),path=require('node:path');
function ordinaryFile(file,minimum){try{const s=fs.lstatSync(file);return s.isFile()&&!s.isSymbolicLink()&&s.size>=minimum;}catch{return false;}}
function populatedDirectory(directory){let handle;try{const s=fs.lstatSync(directory);if(!s.isDirectory()||s.isSymbolicLink())return false;handle=fs.opendirSync(directory);return handle.readSync()!==null;}catch{return false;}finally{handle?.closeSync();}}
function hasLocalWorkspace(appId,configuration){
 if(!['melange','mentat'].includes(appId)||!configuration||typeof configuration.dataDirectory!=='string'||!path.isAbsolute(configuration.dataDirectory))return false;
 if(['ownerGitHubModuleData','ownerGitHubWorkspaceData','ownerGitHubData'].some(key=>Object.hasOwn(configuration,key)))return false;
 const root=configuration.dataDirectory;
 if(appId==='melange')return ordinaryFile(path.join(root,'Moneyball.html'),4096)&&ordinaryFile(path.join(root,'ranks_python.json'),2);
 return populatedDirectory(path.join(root,'.cache','industry-report'))||populatedDirectory(path.join(root,'inputs'))&&populatedDirectory(path.join(root,'config'));
}
module.exports={hasLocalWorkspace};
