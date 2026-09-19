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


INSTALL_HINT = (
    'These official FEC bulk snapshots are not kept in git. Download them with '
    '`python tools/refresh_fec_sources.py --root <folder>`, whose defaults cover every source '
    "family and the 2022, 2024 and 2026 cycles: name this checkout's own inputs folder to fill it "
    'in place, or download elsewhere and add --activate to record that folder in '
    'inputs/active_fec_sources.json. A report build additionally needs the curated '
    'fec_beneficiary/leadership<cycle>.csv files, which the download does not provide.')


def copy_fec_sources(source_root, destination_root, cycles):
    """Stage the selected cycles of bulk FEC evidence, or name what is missing.

    Both folders are checked before anything is copied: staging one and then
    failing on the other would leave a half-populated runtime that a later step
    would read as a complete snapshot. Presence is the only test made here -
    build_industry_report.ps1 checks every required file before it exports.
    """
    folders = ('fec_beneficiary', 'fec_committee_master')
    sources = [Path(source_root) / folder for folder in folders]
    # Resolve the cycle selection first, so an unsupported cycle still fails
    # before any folder is read or written.
    ignores = [source_ignore(source, cycles) for source in sources]
    missing = [str(source) for source in sources if not source.is_dir()]
    if missing:
        raise FileNotFoundError('Missing FEC bulk source folder(s): ' + ', '.join(missing) + '. ' + INSTALL_HINT)
    for folder, source, ignore in zip(folders, sources, ignores):
        shutil.copytree(source, Path(destination_root) / folder, dirs_exist_ok=True, ignore=ignore)
