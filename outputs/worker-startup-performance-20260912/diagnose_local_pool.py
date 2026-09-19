"""Local synthetic transport diagnostic; API transport is a supplied stub."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2] / 'mentat'
sys.path.insert(0, str(root / 'tools'))
from api_request_pool import RequestPool

with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    pool = RequestPool(['synthetic'], directory / 'budget.sqlite', 1,
        transport=lambda spec, key: {'status': 200, 'headers': {}, 'body': json.dumps({'id': spec['id']})})
    try:
        env = os.environ.copy()
        env.update(MENTAT_REQUEST_POOL_URL=pool.start(), MENTAT_REQUEST_POOL_TOKEN=pool.token,
                   R_LIBS_USER=str(root / '.cache/audit-r-library'), NO_PROXY='127.0.0.1,localhost')
        script = directory / 'diagnostic.R'
        script.write_text('''for(f in c("paths.R","schema.R","ingest.R","collect.R","fec_api.R"))source(file.path("%s",f))
specs<-list(list(id="synthetic",url=FEC_API_ENDPOINT,params=list(contributor_employer="SYNTHETIC")))
tryCatch({print(fec_api_default_transport(specs,"unused",1L))},error=function(e){cat("LOCAL FAILURE:",conditionMessage(e),"\\n");quit(status=1)})
''' % (root / 'R').as_posix(), encoding='utf-8')
        result = subprocess.run(['C:/Program Files/R/R-4.6.0/bin/Rscript.exe', str(script)],
                                env=env, capture_output=True, text=True, timeout=10)
        print(result.stdout, result.stderr, 'returncode', result.returncode)
    finally:
        pool.close()
