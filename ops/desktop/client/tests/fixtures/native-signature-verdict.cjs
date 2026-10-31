'use strict';
const PIN='0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30';
function verdict(filename,status=0,thumbprint=PIN){
 const wintrustStatus=({0:0,1:0x800B0004,2:0x800B0100,3:0x80096010,4:0x800B0109})[status];
 return {schemaVersion:1,path:filename,wintrustStatus,thumbprint,selfSigned:true,validAtVerificationTime:true,
  signerError:status===4?wintrustStatus:0,certificateError:status===4?wintrustStatus:0,
  chainErrors:status===4?0x20:0,counterSignerErrors:false,verdict:[0,4].includes(status)?'verified':'refused'};
}
module.exports={verdict,PIN};
