'use strict';
const fs=require('fs'),path=require('path');
const files=process.argv.slice(2);
for(const f of files){
  if(!fs.existsSync(f)){console.log(f+': MISSING');continue;}
  const b=fs.readFileSync(f);let crlf=0,lf=0;
  for(let i=0;i<b.length;i++){if(b[i]===10){if(i>0&&b[i-1]===13)crlf++;else lf++;}}
  const h=require('crypto').createHash('sha256').update(b).digest('hex');
  console.log(path.basename(f)+' | crlf='+crlf+' lonelf='+lf+' | class='+(crlf&&lf?'mixed':crlf?'CRLF':'LF')+' | '+h+' | bytes='+b.length);
}
