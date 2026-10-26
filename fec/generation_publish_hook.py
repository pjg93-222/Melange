"""Optional hand-off from a finished collection (or chain commit) to page publication.

Inert unless MELANGE_GENERATION_PUBLISH names a JSON configuration file:
  {"transport": {"kind": "local", "root": "..."}
             or {"kind": "github-draft", "repository": "pjg93-222/Melange"},
   "stagingRoot": "...", "modules": [...optional extra modules...],
   "partitions": {"module": ["118"]}, "pageBytes": 16777216}

Call shape for a caller such as the Task 1 chain commit, after its data is final:
  after_collection(source, data_root, generation=None) -> publication dict | None

The generation always carries the modules the source installs
(module_application_contracts.COLLECTOR_MODULES); an unknown source or a missing
installed output raises before anything is sealed.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ENVIRONMENT = 'MELANGE_GENERATION_PUBLISH'


def after_collection(source, data_root, generation=None):
    location = os.environ.get(ENVIRONMENT)
    if not location:
        return None
    config = json.loads(Path(location).read_text(encoding='utf-8'))
    packaging = Path(__file__).resolve().parents[1] / 'ops' / 'desktop' / 'packaging'
    if str(packaging) not in sys.path:
        sys.path.insert(0, str(packaging))
    import generation_publish as gp
    from module_application_contracts import COLLECTOR_MODULES, paged_module
    owned = COLLECTOR_MODULES.get(source)
    if not owned:
        raise gp.PublicationError('No paged module is registered for collector source: {}'.format(source))
    partitions = {key: tuple(value) for key, value in config.get('partitions', {}).items()}
    missing = [module.path(part) for module in map(paged_module, owned)
               for part in partitions.get(module.module_id, module.partitions)
               if not (Path(data_root) / module.path(part)).is_file()]
    if missing:
        raise gp.PublicationError('Collector output is not installed: ' + ', '.join(missing))
    modules = tuple(dict.fromkeys((*owned, *(config.get('modules') or ()))))
    now = datetime.now(timezone.utc)
    generation = generation or int(now.timestamp())
    tag = 'module-data-{}-pages-{}'.format(now.strftime('%Y-%m-%d'), generation)
    kind = config['transport']['kind']
    if kind == 'local':
        transport = gp.LocalDirectoryTransport(config['transport']['root'])
    elif kind == 'github-draft':
        transport = gp.GitHubDraftTransport(config['transport']['repository'], tag)
    else:
        raise ValueError('Unsupported generation transport')
    publication = gp.publish_generation(data_root, Path(config['stagingRoot']) / tag, transport,
        release_tag=tag, generation=generation, modules=modules, partitions=partitions,
        page_bytes=config.get('pageBytes', gp.MAX_PAGE_BYTES))
    print(json.dumps({'generationPublished': source, 'modules': list(modules), 'releaseTag': tag,
                      'indexSha256': publication['indexSha256']}),
          flush=True)
    return publication
