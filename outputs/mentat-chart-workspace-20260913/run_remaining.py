import concurrent.futures, json, os, pathlib, subprocess, tempfile, unittest, importlib.util
root=pathlib.Path(__file__).resolve().parents[2]
out=pathlib.Path(__file__).parent
node=r'C:/Program Files/nodejs/node.exe'
r=r'C:/Program Files/R/R-4.6.0/bin/Rscript.exe'
def run(file):
    with tempfile.TemporaryDirectory(prefix='mentat-fix-check-') as tmp:
        env=os.environ.copy()
        env.update(MENTAT_REPORT_DIRECTORY=tmp+'/reports',MENTAT_DATA_ROOT=tmp+'/data',MENTAT_BROWSER_CHANNEL='chrome',MENTAT_PYTHON=os.sys.executable)
        pathlib.Path(tmp+'/reports').mkdir();pathlib.Path(tmp+'/data').mkdir()
        env['PATH']=str(pathlib.Path(os.sys.executable).parent)+os.pathsep+env['PATH']
        env['R_LIBS_USER']='C:/Users/pgoff/AppData/Local/R/win-library/4.6'
        env['NODE_PATH']='C:/Users/pgoff/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
        for key in list(env):
            if key.startswith('FEC_API_KEY'):env.pop(key)
        cmd=([r,str(file)] if file.suffix=='.R' else ['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(file)] if file.suffix=='.ps1' else [node,'--test',str(file)])
        try:
            p=subprocess.run(cmd,cwd=root,env=env,capture_output=True,timeout=180)
            output=p.stdout+p.stderr;code=p.returncode
        except subprocess.TimeoutExpired as e:output=(e.stdout or b'')+(e.stderr or b'');code=124
        (out/(file.name+'.log')).write_bytes(output)
        result=dict(file=file.name,returncode=code)
        print(json.dumps(result),flush=True)
        return result
if __name__=='__main__':
    files=([root/'mentat/tests'/name for name in os.sys.argv[1:]] if len(os.sys.argv)>1 else sorted((root/'mentat/tests').glob('*.R'))+sorted((root/'mentat/tests').glob('*.ps1'))+sorted((root/'mentat/tests').glob('*.cjs'))+sorted((root/'mentat/app/tests').glob('*.test.js')))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,files))
    (out/('retry-results.json' if len(os.sys.argv)>1 else 'remaining-results.json')).write_text(json.dumps(results,indent=2))
