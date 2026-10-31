'use strict';
// Compile an already prepared program with NSIS builtins only. Signing and
// release acceptance remain separate caller responsibilities.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const {isDeepStrictEqual} = require('node:util');
const asar = require('@electron/asar');
const {NtExecutable, NtExecutableResource} = require('resedit');
const {appDefinition} = require('./apps.cjs');
const layout = require('./install-layout.cjs');

const quote = (value, escapeDollars = true) => {
  if (/[\r\n\0]/.test(String(value))) throw new Error('Invalid NSIS definition');
  const text = escapeDollars ? String(value).replace(/\$/g, '$$$$') : String(value);
  return '"' + text.replace(/"/g, '$\\"') + '"';
};
function physical(file, directory = false) {
  const resolved = path.resolve(file);
  const info = fs.lstatSync(resolved);
  if (info.isSymbolicLink() || (directory ? !info.isDirectory() : !info.isFile() || info.nlink !== 1) ||
      fs.realpathSync.native(resolved).toLowerCase() !== resolved.toLowerCase()) {
    throw new Error('A physical ' + (directory ? 'directory' : 'file') + ' is required: ' + resolved);
  }
  return resolved;
}
function payloadFiles(program, executable) {
  // File /r exclusions match basenames. Refuse an ambiguous nested match rather
  // than silently omit another program's file when applying the two overlays.
  const files = new Map(), folded = new Set();
  function walk(directory, prefix) {
    physical(directory, true);
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
      const normalized = relative.replace(/\\/g, '/');
      if (folded.has(normalized.toLowerCase())) throw new Error('Duplicate Windows payload path: ' + relative);
      folded.add(normalized.toLowerCase());
      files.set(normalized, physical(path.join(directory, entry.name)));
    }
  }
  walk(program, '');
  return files;
}
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
// The EnableEmbeddedAsarIntegrityValidation fuse makes Electron refuse to start
// unless the main EXE names exactly this Windows-relative key for this header.
// Same contract as verify_native_release.py verify_asar_integrity, checked
// before compiling so a hand-patched EXE (e.g. "resourcesapp.asar") fails fast.
function requireAsarIntegrity(executable, archive) {
  const value = crypto.createHash('sha256').update(asar.getRawHeader(archive).headerString).digest('hex');
  const entries = NtExecutableResource.from(NtExecutable.from(fs.readFileSync(executable), {ignoreCert:true})).entries
    .filter(entry => entry.type === 'INTEGRITY' && entry.id === 'ELECTRONASAR');
  let actual = null;
  try { actual = entries.length === 1 ? JSON.parse(Buffer.from(entries[0].bin).toString('utf8')) : null; } catch {}
  if (!isDeepStrictEqual(actual, [{file:'resources\\app.asar', alg:'SHA256', value}])) {
    throw new Error('Main executable ASAR integrity differs from the selected app.asar: ' +
      (entries.length === 1 ? Buffer.from(entries[0].bin).toString('utf8') : entries.length + ' integrity resources'));
  }
}
const stamp = file => {
  const value=fs.lstatSync(physical(file),{bigint:true});
  return [value.dev,value.ino,value.mode,value.nlink,value.size,value.mtimeNs,value.ctimeNs].join(':');
};
function exactKeys(value, keys) {
  return value && !Array.isArray(value) && typeof value === 'object' &&
    Object.keys(value).sort().join('|') === [...keys].sort().join('|');
}
const BOOTSTRAP_OVERLAY33 = Object.freeze([
  'data_release_fetch.py',
  'desktop_audit.py',
  'desktop_backend.py',
  'desktop_credentials.py',
  'desktop_figure_renderer.py',
  'desktop_migrations.py',
  'desktop_workspace.py',
  'melange_bootstrap.py',
  'melange_data_paths.py',
  'melange_module_data.py',
  'melange_public_payroll_normalize.py',
  'melange_public_payroll_projection.py',
  'melange_public_provenance.py',
  'mentat_layout.py',
  'mentat_module_data.py',
  'module_application_contracts.py',
  'module_application_inventory.py',
  'module_catalogue_cache.py',
  'module_data_handoff.py',
  'module_data_launch.py',
  'module_data_snapshot.py',
  'module_public_input_installers.py',
  'module_workspace_combined_ui.py',
  'module_workspace_handoff.py',
  'module_workspace_industry_ui.py',
  'module_workspace_inputs.py',
  'module_workspace_installers.py',
  'module_workspace_render.py',
  'module_workspace_ui_templates.py',
  'native_access_state.py',
  'native_credentials.py',
  'terrier_district.py',
  'terrier_github_snapshot.py',
  'terrier_owner.py',
  'terrier_runtime_handoff.py',
  'terrier_standalone.py',
  'workspace_archive.py',
  'workspace_cache.py',
  'workspace_data_contract.py',
  'workspace_graph.py',
  'workspace_melange.py',
  'workspace_mentat.py',
  'workspace_sqlite.py',
]);
const BOOTSTRAP_ADDITIONS33 = Object.freeze([
  'desktop_workspace.py',
  'module_workspace_combined_ui.py',
  'module_workspace_handoff.py',
  'module_workspace_industry_ui.py',
  'module_workspace_inputs.py',
  'module_workspace_installers.py',
  'module_workspace_render.py',
  'module_workspace_ui_templates.py',
  'terrier_runtime_handoff.py',
  'workspace_archive.py',
  'workspace_cache.py',
  'workspace_data_contract.py',
  'workspace_graph.py',
  'workspace_melange.py',
  'workspace_mentat.py',
  'workspace_sqlite.py',
]);
function sourceOverlay(files, appId, version, manifestFile) {
  if (!manifestFile) return {files:new Map(files), inputs:[]};
  manifestFile = physical(manifestFile);
  if (fs.statSync(manifestFile).size > 65536) throw new Error('Source overlay manifest is too large');
  const manifestStamp=stamp(manifestFile), raw=fs.readFileSync(manifestFile), text=raw.toString('utf8');
  const manifest = JSON.parse(text), manifestHash=crypto.createHash('sha256').update(raw).digest('hex');
  // Canonical local manifests also reject duplicate properties and escaped path
  // aliases, without sharing parser implementation with the independent verifier.
  if (![JSON.stringify(manifest),JSON.stringify(manifest,null,2)+'\n'].includes(text) || stamp(manifestFile)!==manifestStamp) {
    throw new Error('Source overlay manifest must be unchanged canonical JSON');
  }
  const prefix = 'resources/runtime/' + appId + '/';
  // Legacy releases retain their old closure. Release33 separately enumerates
  // the reviewed helpers that may be absent from the exact sealed32 baseline.
  const legacyAllowed = new Set(['bootstrap/terrier_standalone.py','bootstrap/module_application_inventory.py',
    'bootstrap/module_application_contracts.py','bootstrap/module_public_input_installers.py',
    'bootstrap/native_access_state.py','bootstrap/module_catalogue_cache.py',
    'source-inventory.json','source-provenance.json',
    ...(appId === 'terrier' ? ['sources/server/research/street_views.py'] : []),
    ...(appId === 'melange' ? ['sources/fec/surfaces/melange_public_data.py'] : [])].map(name => prefix + name));
  const allowed = version === '1.0.33' ? new Set([...BOOTSTRAP_OVERLAY33.map(name => prefix + 'bootstrap/' + name),
    prefix + 'source-inventory.json', prefix + 'source-provenance.json',
    ...(appId === 'melange' ? [prefix + 'sources/fec/surfaces/staffer_graph_snapshot.py', prefix + 'sources/fec/surfaces/staffer_live_service.py'] : [])]) : legacyAllowed;
  const additions = version === '1.0.33' ? new Set(BOOTSTRAP_ADDITIONS33.map(name => prefix + 'bootstrap/' + name))
    : new Set([prefix + 'bootstrap/module_catalogue_cache.py']);
  if (!exactKeys(manifest, ['schemaVersion','appId','version','clientCommit','sourceCommit','files']) ||
      manifest.schemaVersion !== 1 || manifest.appId !== appId || manifest.version !== version ||
      !/^[a-f0-9]{40}$/.test(manifest.clientCommit) || !/^[a-f0-9]{40}$/.test(manifest.sourceCommit) ||
      !Array.isArray(manifest.files) || !manifest.files.length || manifest.files.length > allowed.size) {
    throw new Error('Invalid source overlay identity');
  }
  const root = physical(path.join(path.dirname(manifestFile), 'files'), true);
  const actual = payloadFiles(root, '\0'), selected = new Map(files), seen = new Set(), inputs = [];
  for (const row of manifest.files) {
    if (!exactKeys(row, ['path','bytes','sha256']) || !allowed.has(row.path) || seen.has(row.path) ||
        (!files.has(row.path) && !additions.has(row.path)) || !Number.isSafeInteger(row.bytes) || row.bytes < 0 || row.bytes > 16*1024*1024 ||
        typeof row.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(row.sha256)) throw new Error('Invalid source overlay member');
    seen.add(row.path);
    const source = actual.get(row.path);
    if (!source) throw new Error('Source overlay bytes differ');
    const before=stamp(source);
    if (fs.statSync(source).size !== row.bytes || digest(source) !== row.sha256) throw new Error('Source overlay bytes differ');
    const head = fs.readFileSync(source);
    if (head[0] === 0x4d && head[1] === 0x5a) throw new Error('Source overlays cannot contain native images');
    if (stamp(source)!==before) throw new Error('Source overlay changed during validation');
    selected.set(row.path, source);
    inputs.push({path:source, bytes:row.bytes, sha256:row.sha256, identity:before});
  }
  if (actual.size !== seen.size) throw new Error('Source overlay file inventory is not closed');
  inputs.push({path:manifestFile, bytes:raw.length, sha256:manifestHash, identity:manifestStamp});
  return {files:selected, inputs, manifest:manifestFile, sha256:manifestHash,
    clientCommit:manifest.clientCommit, sourceCommit:manifest.sourceCommit, replacements:manifest.files};
}
function payloadInclude(files) {
  const lines = [];
  let previous = null;
  for (const [relative, source] of [...files].sort(([a],[b]) => a < b ? -1 : a > b ? 1 : 0)) {
    const parts = relative.split('/'), name = parts.pop(), directory = parts.join('\\');
    if (directory !== previous) {
      lines.push('  SetOutPath "$INSTDIR' + (directory ? '\\' + quote(directory).slice(1,-1) : '') + '"', '  IfErrors extraction_failed');
      previous = directory;
    }
    // File's source is resolved at compile time; dollars there are literal.
    lines.push('  File ' + quote('/oname=' + name) + ' ' + quote(source, false), '  IfErrors extraction_failed');
  }
  return lines.join('\n') + '\n';
}
function build({appId, version, program, output, makensis, appExecutable, appAsar, sourceOverlay:overlayManifest, compression = 'lzma'}) {
  if (process.platform !== 'win32') throw new Error('This native installer build requires Windows');
  if (!['lzma', 'zlib'].includes(compression)) throw new Error('Compression must be lzma or zlib');
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
  requireAsarIntegrity(appExecutable, appAsar);
  if (overlayManifest && (layout.isUnder(path.resolve(overlayManifest), program) ||
      layout.isUnder(program, path.dirname(path.resolve(overlayManifest))))) throw new Error('Source overlay must be outside the retained base');
  const retainedFiles=payloadFiles(program, executable);
  const selected = sourceOverlay(retainedFiles, appId, version, overlayManifest);
  selected.files.set(executable, appExecutable);
  selected.files.set('resources/app.asar', appAsar);
  // The installer's running-instance guard probes this exact payload file.
  const backendExecutable = 'resources\\runtime\\' + app.id + '\\python\\python.exe';
  if (!selected.files.has(backendExecutable.replace(/\\/g, '/'))) throw new Error('Payload is missing the backend interpreter: ' + backendExecutable);
  const fileCount = selected.files.size;
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
    sourceProgram:program, compiler, compression, createdAt:new Date().toISOString()
  }, null, 2) + '\n', {flag:'wx'});
  const include = path.join(compilerWorkDirectory, 'payload.nsh');
  fs.writeFileSync(include, payloadInclude(selected.files), {flag:'wx'});
  const includeHash = digest(include);
  const definitions = {
    PF_PRODUCT:app.name, PF_APP_ID:app.applicationId, PF_VERSION:version, PF_EXE:executable, PF_BACKEND_EXE:backendExecutable,
    PF_PAYLOAD_INCLUDE:include,
    PF_OUTPUT:output, PF_ICON:icon, PF_LANGUAGE:language, PF_COMPRESSION:compression,
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
  const finalOverlay=sourceOverlay(retainedFiles,appId,version,overlayManifest);
  if (digest(include) !== includeHash || JSON.stringify(finalOverlay.inputs)!==JSON.stringify(selected.inputs)) {
    throw new Error('Source overlay or exact payload include changed during compilation');
  }
  const receipt = {
    schemaVersion:1, appId, version, format:'builtin-nsis-v1', desktopUninstaller:false, installerPlugins:[],
    sourceProgram:program, appExecutable, appAsar, inputFileCount:fileCount, compiler, compilerWorkDirectory,
    payloadInclude:include, payloadIncludeSha256:includeHash,
    sourceOverlay:selected.manifest ? {path:selected.manifest, sha256:selected.sha256,
      clientCommit:selected.clientCommit, sourceCommit:selected.sourceCommit, files:selected.replacements} : null,
    generatedScript:script, installer:output,
    compression:{method:compression, solid:false, ...(compression === 'lzma' ? {dictionaryMiB:8} : {})},
    verificationStage:'Not run; this command only compiles the installer. Signing and release acceptance are separate.'
  };
  fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n', {flag:'wx'});
  return receipt;
}
function argumentsFor(argv) {
  const allowed = new Set(['app', 'version', 'program', 'output', 'makensis', 'app-executable', 'app-asar', 'source-overlay', 'compression']);
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index].replace(/^--/, '');
    if (!argv[index].startsWith('--') || !allowed.has(key) || Object.hasOwn(args, key) ||
        !argv[index + 1] || argv[index + 1].startsWith('--')) throw new Error('Invalid or repeated argument: ' + argv[index]);
    args[key] = argv[index + 1];
  }
  for (const key of ['app', 'version', 'program', 'output', 'makensis']) if (!args[key]) throw new Error('Missing --' + key);
  return {appId:args.app, version:args.version, program:args.program, output:args.output, makensis:args.makensis,
    appExecutable:args['app-executable'], appAsar:args['app-asar'], sourceOverlay:args['source-overlay'], compression:args.compression || 'lzma'};
}
module.exports = {build, argumentsFor, payloadFiles, sourceOverlay, payloadInclude, requireAsarIntegrity};
if (require.main === module) {
  try { console.log(JSON.stringify(build(argumentsFor(process.argv.slice(2))))); }
  catch (error) { console.error(error); process.exitCode = 1; }
}
