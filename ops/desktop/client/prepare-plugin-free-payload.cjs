'use strict';
// Produce only the two versioned application overlays. Existing signed runtime
// and vendor files remain read-only inputs to the native installer compiler.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const asar = require('@electron/asar');
const {NtExecutable, NtExecutableResource, Resource} = require('resedit');
const {appDefinition} = require('./apps.cjs');

async function prepare({appId, version, program, output}) {
  const app = appDefinition(appId);
  if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error('A numeric release version is required');
  program = path.resolve(program); output = path.resolve(output);
  if (fs.existsSync(output)) throw new Error('Use a new overlay output directory');
  if (fs.realpathSync.native(program).toLowerCase() !== program.toLowerCase()) throw new Error('Program must be a physical directory');
  fs.mkdirSync(output, {recursive:true});
  const sourceAsar = path.join(program, 'resources', 'app.asar');
  const sourceExe = path.join(program, app.name + '.exe');
  const client = path.join(output, 'client');
  asar.extractAll(sourceAsar, client);
  const packagePath = path.join(client, 'package.json');
  const metadata = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
  if (metadata.desktopAppConfig?.appId !== app.id || metadata.desktopAppConfig?.desktopUninstaller !== false) {
    throw new Error('The source payload must belong to the selected app and have no uninstaller');
  }
  const previousVersion = metadata.version;
  metadata.version = version;
  fs.writeFileSync(packagePath, JSON.stringify(metadata, null, 2) + '\n');
  const newAsar = path.join(output, 'app.asar');
  await asar.createPackage(client, newAsar);
  const header = asar.getRawHeader(newAsar).headerString;
  if (typeof header !== 'string') throw new Error('ASAR header is unavailable');
  const headerHash = crypto.createHash('sha256').update(header).digest('hex');
  // The owned main EXE must be re-signed after changing version/integrity resources.
  const executable = NtExecutable.from(fs.readFileSync(sourceExe), {ignoreCert:true});
  const resources = NtExecutableResource.from(executable);
  const versions = Resource.VersionInfo.fromEntries(resources.entries);
  if (versions.length !== 1) throw new Error('Ambiguous application version resource');
  const languages = versions[0].getAllLanguagesForStringValues();
  if (languages.length !== 1) throw new Error('Ambiguous application version language');
  versions[0].setFileVersion(version + '.0');
  versions[0].setProductVersion(version + '.0');
  versions[0].setStringValues(languages[0], {FileVersion:version, ProductVersion:version});
  versions[0].outputToResourceEntries(resources.entries);
  const entries = resources.entries.filter(entry => entry.type === 'INTEGRITY' && entry.id === 'ELECTRONASAR');
  if (entries.length !== 1) throw new Error('Existing Electron ASAR integrity resource required');
  entries[0].bin = Buffer.from(JSON.stringify([{file:'resources\\app.asar',alg:'SHA256',value:headerHash}]));
  resources.outputResource(executable);
  const newExe = path.join(output, app.name + '.exe');
  fs.writeFileSync(newExe, Buffer.from(executable.generate()), {flag:'wx'});
  const thumbprint = '0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30';
  const signtool = 'C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.28000.0\\x64\\signtool.exe';
  const signingOutput = execFileSync(signtool,
    ['sign','/sha1',thumbprint,'/s','My','/fd','sha256','/tr','http://timestamp.digicert.com','/td','sha256',newExe],
    {windowsHide:true,encoding:'utf8',maxBuffer:1024*1024});
  fs.writeFileSync(path.join(output,'signing.log'),signingOutput);
  const receipt = {appId,version,previousVersion,sourceProgram:program,appExecutable:newExe,appAsar:newAsar,
    asarHeaderSha256:headerHash,signing:{tool:signtool,exitCode:0,thumbprint,
      timestampUrl:'http://timestamp.digicert.com',sha256:crypto.createHash('sha256').update(fs.readFileSync(newExe)).digest('hex')},
    verificationStage:'Skipped at the user\'s explicit request; no final payload or application acceptance check performed'};
  fs.writeFileSync(path.join(output,'payload-build.json'),JSON.stringify(receipt,null,2)+'\n');
  return receipt;
}
module.exports = {prepare};
if (require.main === module) {
  const args = Object.fromEntries(process.argv.slice(2).reduce((rows,value,index,all) =>
    index % 2 ? rows : rows.concat([[value.replace(/^--/,''),all[index+1]]]),[]));
  prepare({appId:args.app,version:args.version,program:args.program,output:args.output})
    .then(value=>console.log(JSON.stringify(value))).catch(error=>{console.error(error);process.exitCode=1;});
}
