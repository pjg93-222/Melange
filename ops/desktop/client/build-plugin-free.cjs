'use strict';
// Compile an already prepared program with NSIS builtins only. Signing and
// release acceptance remain separate caller responsibilities.
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const asar = require('@electron/asar');
const {appDefinition} = require('./apps.cjs');
const layout = require('./install-layout.cjs');

const quote = value => {
  if (/[\r\n\0]/.test(String(value))) throw new Error('Invalid NSIS definition');
  return '"' + String(value).replace(/\$/g, '$$$$').replace(/"/g, '$\\"') + '"';
};
function physical(file, directory = false) {
  const resolved = path.resolve(file);
  const info = fs.lstatSync(resolved);
  if (info.isSymbolicLink() || (directory ? !info.isDirectory() : !info.isFile()) ||
      fs.realpathSync.native(resolved).toLowerCase() !== resolved.toLowerCase()) {
    throw new Error('A physical ' + (directory ? 'directory' : 'file') + ' is required: ' + resolved);
  }
  return resolved;
}
function payloadShape(program, executable) {
  // File /r exclusions match basenames. Refuse an ambiguous nested match rather
  // than silently omit another program's file when applying the two overlays.
  let count = 0;
  function walk(directory, prefix) {
    for (const entry of fs.readdirSync(directory, {withFileTypes:true})) {
      const relative = prefix ? prefix + '\\' + entry.name : entry.name;
      if (entry.isSymbolicLink() || (!entry.isDirectory() && !entry.isFile())) {
        throw new Error('Payload links and special files are not supported: ' + relative);
      }
      if (relative.length > layout.LAYOUT.deepestRelativeBudget) {
        throw new Error('Payload exceeds the Windows relative-path budget: ' + relative);
      }
      if (entry.isDirectory()) { walk(path.join(directory, entry.name), relative); continue; }
      if (/^uninstall.*\.exe$/i.test(entry.name)) throw new Error('Payload contains an uninstaller: ' + relative);
      if ((entry.name.toLowerCase() === executable.toLowerCase() && relative !== executable) ||
          (entry.name.toLowerCase() === 'app.asar' && relative !== 'resources\\app.asar')) {
        throw new Error('Ambiguous overlay basename: ' + relative);
      }
      count++;
    }
  }
  walk(program, '');
  return count;
}
function build({appId, version, program, output, makensis, appExecutable, appAsar}) {
  if (process.platform !== 'win32') throw new Error('This native installer build requires Windows');
  const app = appDefinition(appId);
  if (!/^\d+\.\d+\.\d+$/.test(version) || version.split('.').some(value => Number(value) > 65535)) {
    throw new Error('A numeric Windows release version is required');
  }
  program = physical(program, true);
  const executable = app.name + '.exe';
  appExecutable = physical(appExecutable || path.join(program, executable));
  appAsar = physical(appAsar || path.join(program, 'resources', 'app.asar'));
  const metadata = JSON.parse(asar.extractFile(appAsar, 'package.json').toString('utf8'));
  if (metadata.version !== version || metadata.name !== app.id + '-desktop' ||
      metadata.desktopAppConfig?.appId !== app.id || metadata.desktopAppConfig?.desktopUninstaller !== false) {
    throw new Error('Selected ASAR must match the requested app/version and no-uninstaller contract');
  }
  const fileCount = payloadShape(program, executable);
  let compiler = path.resolve(makensis);
  if (fs.statSync(compiler).isDirectory()) {
    compiler = [path.join(compiler, 'Bin', 'makensis.exe'), path.join(compiler, 'makensis.exe')]
      .find(candidate => fs.existsSync(candidate));
    if (!compiler) throw new Error('NSIS compiler was not found in the supplied directory');
  }
  compiler = physical(compiler);
  const compilerParent = path.dirname(compiler);
  const nsisDirectory = path.basename(compilerParent).toLowerCase() === 'bin' ? path.dirname(compilerParent) : compilerParent;
  const language = physical(path.join(nsisDirectory, 'Contrib', 'Language files', 'English.nlf'));
  const icon = physical(path.join(__dirname, 'icons', app.id + '.ico'));
  output = path.resolve(output);
  if (!output.toLowerCase().endsWith('.exe') || output.toLowerCase() === program.toLowerCase() ||
      layout.isUnder(output, program) || layout.isUnder(program, output)) {
    throw new Error('Installer output must be an EXE outside the input program');
  }
  const script = output + '.plugin-free.nsi';
  const receiptPath = output + '.build.json';
  const compilerWorkDirectory = output + '.work';
  for (const file of [output, script, receiptPath, compilerWorkDirectory]) {
    if (fs.existsSync(file)) throw new Error('Use a fresh installer output path: ' + file);
  }
  fs.mkdirSync(path.dirname(output), {recursive:true});
  physical(path.dirname(output), true);
  // Keep compiler scratch local to this fresh output, including on failure.
  // The caller can retire this exact owned directory after preserving evidence.
  fs.mkdirSync(compilerWorkDirectory);
  physical(compilerWorkDirectory, true);
  fs.writeFileSync(path.join(compilerWorkDirectory, 'owner.json'), JSON.stringify({
    schemaVersion:1, purpose:'plugin-free-nsis-compiler', appId, version, output,
    sourceProgram:program, compiler, createdAt:new Date().toISOString()
  }, null, 2) + '\n', {flag:'wx'});
  const definitions = {
    PF_PRODUCT:app.name, PF_APP_ID:app.applicationId, PF_VERSION:version, PF_EXE:executable,
    PF_PROGRAM:program, PF_EXECUTABLE_SOURCE:appExecutable, PF_ASAR_SOURCE:appAsar,
    PF_OUTPUT:output, PF_ICON:icon, PF_LANGUAGE:language,
    PF_ROOT:layout.LAYOUT.rootName, PF_FOLDER:layout.fill(layout.LAYOUT.appFolder, {product:app.name, version}),
    PF_DOWNLOADS_GUID:layout.LAYOUT.downloadsKnownFolder, PF_MAX_DIRECTORY:String(layout.maxDirectory())
  };
  const source = Object.entries(definitions).map(([key, value]) => '!define ' + key + ' ' + quote(value)).join('\n') + '\n' +
    fs.readFileSync(path.join(__dirname, 'plugin-free-installer.nsi'), 'utf8');
  fs.writeFileSync(script, source, {flag:'wx'});
  const compiled = spawnSync(compiler, ['/INPUTCHARSET', 'UTF8', '/V3', '/WX', script], {
    stdio:'inherit', windowsHide:true,
    env:{...process.env, NSISDIR:nsisDirectory, TEMP:compilerWorkDirectory, TMP:compilerWorkDirectory}
  });
  if (compiled.error) throw compiled.error;
  if (compiled.status !== 0) throw new Error('NSIS compilation failed (' + compiled.status + '); generated script retained at ' + script);
  const receipt = {
    schemaVersion:1, appId, version, format:'builtin-nsis-v1', desktopUninstaller:false, installerPlugins:[],
    sourceProgram:program, appExecutable, appAsar, inputFileCount:fileCount, compiler, compilerWorkDirectory,
    generatedScript:script, installer:output, compression:{method:'lzma', solid:false, dictionaryMiB:8},
    verificationStage:'Not run; this command only compiles the installer. Signing and release acceptance are separate.'
  };
  fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n', {flag:'wx'});
  return receipt;
}
function argumentsFor(argv) {
  const allowed = new Set(['app', 'version', 'program', 'output', 'makensis', 'app-executable', 'app-asar']);
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index].replace(/^--/, '');
    if (!argv[index].startsWith('--') || !allowed.has(key) || Object.hasOwn(args, key) ||
        !argv[index + 1] || argv[index + 1].startsWith('--')) throw new Error('Invalid or repeated argument: ' + argv[index]);
    args[key] = argv[index + 1];
  }
  for (const key of ['app', 'version', 'program', 'output', 'makensis']) if (!args[key]) throw new Error('Missing --' + key);
  return {appId:args.app, version:args.version, program:args.program, output:args.output, makensis:args.makensis,
    appExecutable:args['app-executable'], appAsar:args['app-asar']};
}
module.exports = {build, argumentsFor};
if (require.main === module) {
  try { console.log(JSON.stringify(build(argumentsFor(process.argv.slice(2))))); }
  catch (error) { console.error(error); process.exitCode = 1; }
}
