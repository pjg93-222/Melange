"""Copy private FEC input snapshots for just the requested election cycles."""
from pathlib import Path
import re
import shutil


def source_ignore(source_folder, cycles):
    """Keep shared metadata and all selected-cycle evidence, excluding caches."""
    source_folder = Path(source_folder)
    selected = {int(cycle) for cycle in cycles}
    if not selected or not selected <= {2022, 2024, 2026}:
        raise ValueError('Select supported election cycles before copying FEC inputs.')
    transient = shutil.ignore_patterns('*.sqlite', '*.pending*', 'transfer-index-*', 'cache')

    def ignore(directory, names):
        excluded = set(transient(directory, names))
        if Path(directory) == source_folder:
            for name in names:
                bulk = re.fullmatch(r'(?:cm|cn|ccl|oth|pas2)(22|24|26)(?:\.zip)?', name, re.I)
                leadership = re.fullmatch(r'leadership(2022|2024|2026)\.csv', name, re.I)
                cycle = 2000 + int(bulk[1]) if bulk else int(leadership[1]) if leadership else None
                if cycle is not None and cycle not in selected:
                    excluded.add(name)
        return excluded

    return ignore


def copy_fec_sources(source_root, destination_root, cycles):
    for folder in ('fec_beneficiary', 'fec_committee_master'):
        source = Path(source_root) / folder
        shutil.copytree(source, Path(destination_root) / folder, dirs_exist_ok=True,
                        ignore=source_ignore(source, cycles))
