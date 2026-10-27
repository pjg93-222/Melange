'use strict';
// Synthetic certificate/key generated only in memory for cryptographic tests.
const crypto=require('node:crypto');
function der(tag,...values){const body=Buffer.concat(values.map(value=>Buffer.isBuffer(value)?value:Buffer.from(value)));let length;if(body.length<128)length=Buffer.from([body.length]);else{const bytes=[];for(let n=body.length;n;n=Math.floor(n/256))bytes.unshift(n%256);length=Buffer.from([0x80|bytes.length,...bytes]);}return Buffer.concat([Buffer.from([tag]),length,body]);}
function oid(value){const parts=value.split('.').map(Number),bytes=[40*parts[0]+parts[1]];for(const n of parts.slice(2)){const encoded=[n&127];let rest=Math.floor(n/128);while(rest){encoded.unshift(0x80|(rest&127));rest=Math.floor(rest/128);}bytes.push(...encoded);}return der(6,Buffer.from(bytes));}
function signingFixture(){
 const keys=crypto.generateKeyPairSync('rsa',{modulusLength:2048});
 const algorithm=der(0x30,oid('1.2.840.113549.1.1.11'),der(5,Buffer.alloc(0)));
 const name=der(0x30,der(0x31,der(0x30,oid('2.5.4.3'),der(12,'Synthetic ZIP publisher fixture'))));
 const time=value=>der(23,new Date(value).toISOString().slice(2,19).replace(/[-:T]/g,'')+'Z');
 const validity=der(0x30,time(Date.now()-86400000),time(Date.now()+365*86400000));
 const usage=der(0xa3,der(0x30,der(0x30,oid('2.5.29.37'),der(4,der(0x30,oid('1.3.6.1.5.5.7.3.3'))))));
 const tbs=der(0x30,der(0xa0,der(2,Buffer.from([2]))),der(2,Buffer.from([1])),algorithm,name,validity,name,keys.publicKey.export({type:'spki',format:'der'}),usage);
 const certificate=der(0x30,tbs,algorithm,der(3,Buffer.from([0]),crypto.sign('sha256',tbs,keys.privateKey)));
 return {certificate,thumbprint:crypto.createHash('sha1').update(certificate).digest('hex').toUpperCase(),sign:payload=>crypto.sign('sha256',payload,{key:keys.privateKey,padding:crypto.constants.RSA_PKCS1_PADDING})};
}
module.exports={signingFixture};
