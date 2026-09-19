const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '../../..');
const mode = process.argv[2] || 'unit';
const tests = fs.readdirSync(path.join(root, 'mentat/tests')).filter(n => n.endsWith('.cjs') && n.includes('browser') === (mode === 'browser')).sort().map(n => path.join(root, 'mentat/tests', n));
if (mode === 'unit') tests.push(path.join(root, 'mentat/app/tests/chart-studio-core.test.js'));
const env = {...process.env, MENTAT_PYTHON: 'C:/Users/pgoff/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe', MENTAT_NODE_MODULES:'C:/Users/pgoff/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'};
const results = [];
for (const file of tests) {
  const started = Date.now();
  const result = spawnSync(process.execPath, ['--test', '--test-reporter=tap', file], {cwd:root, env, encoding:'utf8', timeout:240000, windowsHide:true, maxBuffer:16777216});
  const output = (result.stdout || '') + (result.stderr || '');
  const item = {file: path.relative(root,file), exit:result.status, signal:result.signal, error:result.error?.message, elapsed_seconds:(Date.now()-started)/1000, tests:output.match(/^# tests (\d+)/m)?.[1], pass:output.match(/^# pass (\d+)/m)?.[1], fail:output.match(/^# fail (\d+)/m)?.[1], skipped:output.match(/^# skipped (\d+)/m)?.[1]};
  fs.writeFileSync(path.join(__dirname,path.basename(file)+'.log'),output);
  results.push(item);
  fs.writeFileSync(path.join(__dirname,mode+'-results.json'),JSON.stringify(results,null,2)+'\n');
  console.log(JSON.stringify(item));
}
console.log(JSON.stringify({files:results.length,failed_files:results.filter(r=>r.exit!==0).length,tests:results.reduce((n,r)=>n+Number(r.tests||0),0),pass:results.reduce((n,r)=>n+Number(r.pass||0),0),fail:results.reduce((n,r)=>n+Number(r.fail||0),0)}));
