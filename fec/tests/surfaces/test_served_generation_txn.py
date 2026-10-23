"""Served staffer-live generations under the chain transaction (fec/surfaces/staffer_live_generation.py, fec/chain_transaction.py).

The served workspace is a pointer (data/system/staffer_live_active.json, inside a chain COPY_TREE) naming one complete generation
directory.  These cases prove, on synthetic temp roots with a tiny writer only (no pipeline, no live data, no network):
  1. a build that dies after N of M files, and a chain step that fails after a complete flip, both leave readers on G1, byte-exact;
  2. a chain that dies without commit or rollback is restored to G1 by recover() at the next start, and an open journal keeps G1
     from being pruned meanwhile;
  3. success serves G2 (manifest verifies), keeps G1 and prunes G0;
  4. a terminal audit_full.py failure (ROLLBACK_EXEMPT, committed as run_pipeline does) keeps G2;
  5. the resolver falls back to the legacy approved/ directory whenever the pointer cannot be trusted, and the live server,
     the alias receipt and the desktop backend follow it.
"""
import http.client
import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

FEC = Path(__file__).resolve().parents[2]
REPO = FEC.parent
for _path in (str(FEC), str(REPO)):
    if _path not in sys.path:
        sys.path.insert(0, _path)
import chain_transaction as CT  # noqa: E402
from surfaces import staffer_live_generation as G  # noqa: E402

FILES = 8   # files per synthetic generation: well under the 50-file / 2 MiB fixture budget


def quiet(*_args, **_kwargs):
    pass


@pytest.fixture(autouse=True)
def _isolated_staging(monkeypatch, tmp_path):
    monkeypatch.setenv(CT.MIN_FREE_GB_ENV, '0')
    monkeypatch.setenv(CT.TXN_DIR_ENV, str(tmp_path / 'chain_txn'))           # staging stays inside this test's tmp dir
    monkeypatch.setenv(CT.DATA_ROOT_ENV, str(tmp_path / 'no_such_melange_data'))
    monkeypatch.delenv(G.RUN_ID_ENV, raising=False)
    G._resolved.clear()


@pytest.fixture
def root(tmp_path):
    base = tmp_path / 'root'
    (base / 'data' / 'system').mkdir(parents=True)
    (base / 'data' / 'system' / 'system_manifest.json').write_text('{"stores": []}\n', encoding='utf-8', newline='\n')
    legacy = G.legacy_dir(base)
    (legacy / 'data').mkdir(parents=True)
    (legacy / 'app.js').write_bytes(b'legacy\n')
    return base


def writer(tag, fail_after=None):
    """A tiny stand-in for build_clean_workspace.build(): FILES files whose bytes name the generation."""
    def write(out):
        for n in range(FILES):
            if fail_after is not None and n == fail_after:
                raise RuntimeError('injected build failure after %d of %d files' % (n, FILES))
            rel = 'app.js' if n == 0 else ('data/member-%d.json' % n if n % 2 else 'frame-%d.html' % n)
            path = out / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('%s %s\r\n' % (tag, rel)).encode('utf-8') * 16)
    return write


def pointer_bytes(root):
    return G.pointer_path(root).read_bytes()


def assert_serving(root, generation):
    assert G.active_generation(root) == generation
    assert G.active_dir(root) == G.generation_dir(root, generation)
    assert G.verify_generation(root, generation) == []                       # every byte equals its manifest
    assert (G.active_dir(root) / 'app.js').read_bytes().startswith(generation.encode('utf-8') + b' app.js')


def journal_state(root):
    base = CT.txn_base(str(root))
    states = [CT._read_journal(os.path.join(base, name)) for name in sorted(os.listdir(base))]
    return [j['state'] for j in states if j]


# ---- 1. a failed run leaves readers on the complete previous generation -------------------------------------------------------

def test_build_failure_mid_generation_rolls_back_to_g1(root):
    G.publish_generation(root, writer('G1'), 'G1', log=quiet)
    before = pointer_bytes(root)
    with pytest.raises(RuntimeError, match='injected build failure'):
        with CT.transaction(root, run_id='fail-mid-build', log=quiet):
            G.publish_generation(root, writer('G2', fail_after=5), 'G2', log=quiet)
    assert pointer_bytes(root) == before
    assert_serving(root, 'G1')
    assert G.read_pointer(root)['generation'] == 'G1'                        # the partial G2 is never pointed at
    assert not G.generation_dir(root, 'G2').exists()
    assert journal_state(root) == [CT.ROLLED_BACK]


def test_chain_failure_after_a_complete_flip_restores_the_g1_pointer(root):
    G.publish_generation(root, writer('G1'), 'G1', log=quiet)
    before = pointer_bytes(root)
    with pytest.raises(RuntimeError, match='a later chain step failed'):
        with CT.transaction(root, run_id='fail-after-flip', log=quiet):
            G.publish_generation(root, writer('G2'), 'G2', log=quiet)
            assert_serving(root, 'G2')
            raise RuntimeError('a later chain step failed')
    assert pointer_bytes(root) == before                                     # restored byte-exact by rollback()
    assert_serving(root, 'G1')
    assert G.verify_generation(root, 'G2') == []                             # complete, kept on disk, not served
    assert journal_state(root) == [CT.ROLLED_BACK]


def test_first_generation_rolled_back_falls_back_to_legacy(root):
    with pytest.raises(RuntimeError):
        with CT.transaction(root, run_id='first', log=quiet):
            G.publish_generation(root, writer('G1'), 'G1', log=quiet)
            raise RuntimeError('a later chain step failed')
    assert not G.pointer_path(root).exists()                                 # a new file in scope: removed by rollback()
    assert G.active_dir(root) == G.legacy_dir(root)


# ---- 2. a chain that dies is recovered at the next start -----------------------------------------------------------------------

def test_crash_after_flip_is_recovered_to_g1(root):
    G.publish_generation(root, writer('G1'), 'G1', log=quiet)
    before = pointer_bytes(root)
    txn = CT.begin(root, run_id='killed', log=quiet)
    G.publish_generation(root, writer('G2'), 'G2', log=quiet)
    G.publish_generation(root, writer('G3'), 'G3', log=quiet)                # G1 is now two flips old ...
    assert G.verify_generation(root, 'G1') == []                             # ... yet the OPEN journal's before-image names it
    assert txn.state == CT.OPEN
    del txn                                                                  # process death: neither commit() nor rollback()
    assert CT.recover(root, log=quiet) == ['killed']
    assert pointer_bytes(root) == before
    assert_serving(root, 'G1')
    assert journal_state(root) == [CT.ROLLED_BACK]


# ---- 3. success ----------------------------------------------------------------------------------------------------------------

def test_success_serves_g2_keeps_g1_and_prunes_g0(root):
    G.publish_generation(root, writer('G0'), 'G0', log=quiet)
    G.publish_generation(root, writer('G1'), 'G1', log=quiet)
    with CT.transaction(root, run_id='ok', log=quiet) as txn:
        published = G.publish_generation(root, writer('G2'), 'G2', log=quiet)
        txn.commit()
    assert published['previous'] == 'G1' and published['pruned'] == ['G0']
    assert_serving(root, 'G2')
    assert G.verify_generation(root, 'G1') == []
    assert not G.generation_dir(root, 'G0').exists()
    pointer = G.read_pointer(root)
    assert pointer['path'] == 'fec/surfaces/staffer_live/generations/G2' and pointer['files'] == FILES
    assert journal_state(root) == [CT.COMMITTED]


def test_a_partial_directory_left_by_a_dead_build_is_pruned_and_never_served(root):
    G.publish_generation(root, writer('G1'), 'G1', log=quiet)
    orphan = G.generation_dir(root, 'G1b')
    orphan.mkdir()
    writer('G1b')(orphan)                                                    # a build killed before its manifest was written
    assert G.active_generation(root) == 'G1'
    G.publish_generation(root, writer('G2'), 'G2', log=quiet)
    assert not orphan.exists()
    assert sorted(p.name for p in G.generations_dir(root).iterdir()) == ['G1', 'G2']


# ---- 4. ROLLBACK_EXEMPT: a failing terminal audit keeps the complete vintage -------------------------------------------------

def test_terminal_audit_failure_commits_and_keeps_g2(root):
    G.publish_generation(root, writer('G1'), 'G1', log=quiet)
    script = 'audit_full.py'
    with CT.transaction(root, run_id='audit-red', log=quiet) as txn:
        G.publish_generation(root, writer('G2'), 'G2', log=quiet)
        if script in CT.ROLLBACK_EXEMPT:                                     # fec/run_pipeline.py, the terminal-step branch
            txn.commit('terminal verifier %s failed after every producer succeeded; LIVE is one complete vintage' % script)
        # run_pipeline then returns 1 from inside the transaction; __exit__ must not roll a COMMITTED run back
    assert_serving(root, 'G2')
    assert journal_state(root) == [CT.COMMITTED]


# ---- 5. resolver fallback and the readers bound to it ------------------------------------------------------------------------

def test_resolver_falls_back_to_legacy_unless_the_pointer_names_a_sealed_generation(root):
    legacy = G.legacy_dir(root)
    assert G.active_dir(root) == legacy                                      # no pointer
    G.pointer_path(root).write_text('{not json', encoding='utf-8', newline='\n')
    assert G.active_dir(root) == legacy                                      # unreadable pointer
    unsealed = G.generation_dir(root, 'G9')
    unsealed.mkdir(parents=True)
    writer('G9')(unsealed)                                                   # complete bytes, but no manifest.json
    doc = {'schema': G.POINTER_SCHEMA, 'generation': 'G9', 'path': G.GENERATIONS_REL + '/G9', 'files': FILES,
           'sha256_manifest': '0' * 64, 'written_at': '2026-10-23T00:00:00Z'}
    G.pointer_path(root).write_text(json.dumps(doc), encoding='utf-8', newline='\n')
    assert G.active_dir(root) == legacy                                      # pointer to a generation without a manifest
    for bad in ('..', '../approved', 'G1/../../x', ''):
        G.pointer_path(root).write_text(json.dumps(dict(doc, generation=bad, path=G.GENERATIONS_REL + '/' + bad)),
                                        encoding='utf-8', newline='\n')
        assert G.read_pointer(root) is None and G.active_dir(root) == legacy  # never a path outside generations/
    G.publish_generation(root, writer('G1'), 'G1', log=quiet)
    assert G.active_dir(root) == G.generation_dir(root, 'G1')               # valid pointer
    (G.generation_dir(root, 'G1') / G.MANIFEST_NAME).write_bytes(b'{"tampered": true}\n')
    assert G.active_dir(root) == legacy                                      # manifest no longer what the pointer sealed
    other = root / 'installed-assets'                                        # not the <root>/fec/surfaces/staffer_live layout
    assert G.served_dir(other) == other / 'approved'


def test_live_server_follows_the_pointer_and_a_rollback(root, monkeypatch):
    from fec.surfaces import staffer_live_server as live
    assets = root / 'fec' / 'surfaces' / 'staffer_live'
    monkeypatch.setattr(live, 'ASSETS', assets)
    live._approved_cache.clear()
    server = live.WorkspaceServer(('127.0.0.1', 0), live.Handler)
    server.dashboard = SimpleNamespace(source_root=root)
    server.dashboard_file = 'Moneyball_Redesign.html'
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()

    def get(path):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=5)
        try:
            connection.request('GET', path)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()
    try:
        assert get('/staffer-live/approved/app.js') == (200, b'legacy\n')            # no generation yet: legacy
        G.publish_generation(root, writer('G1'), 'G1', log=quiet)
        status, body = get('/staffer-live/approved/app.js')
        assert status == 200 and body.startswith(b'G1 app.js')
        with pytest.raises(RuntimeError):
            with CT.transaction(root, run_id='server-rollback', log=quiet):
                G.publish_generation(root, writer('G2'), 'G2', log=quiet)
                status, body = get('/staffer-live/approved/data/member-1.json')
                assert status == 200 and body.startswith(b'G2 data/member-1.json')
                raise RuntimeError('a later chain step failed')
        status, body = get('/staffer-live/approved/app.js')
        assert status == 200 and body.startswith(b'G1 app.js')                       # the restored pointer, at once
        assert get('/staffer-live/approved/../generations/G2/app.js')[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        live._approved_cache.clear()


def test_alias_receipt_currency_is_the_served_generation_id(root):
    from surfaces import sync_live_dashboard_alias as alias
    for name in alias.CLEAN_INPUTS:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text('input ' + name, encoding='utf-8', newline='\n')
    (root / 'Moneyball.html').write_text('<html>generated</html>', encoding='utf-8', newline='\n')
    shell = b'<!doctype html>\n<!-- melange-clean-workspace-v2 -->\nshell'
    (root / 'Moneyball_Redesign.html').write_bytes(shell)
    (root / 'data' / 'engine').mkdir(parents=True)
    G.publish_generation(root, writer('G1'), 'G1', log=quiet)

    def receipt(generation):
        doc = {'schema': 'live-dashboard-alias-v1', 'status': 'PASS', 'mode': alias.CLEAN_MODE, 'sha256': alias.digest(root / 'Moneyball_Redesign.html'),
               'source_sha256': alias.digest(root / 'Moneyball.html'), 'workspace_inputs_sha256': alias.clean_inputs(root),
               'served_generation': generation}
        (root / alias.RECEIPT).write_text(json.dumps(doc), encoding='utf-8', newline='\n')
    receipt('G1')
    assert alias.clean_workspace_current(root)
    G.publish_generation(root, writer('G2'), 'G2', log=quiet)                # a newer generation is served
    assert not alias.clean_workspace_current(root)                           # the receipt binds G1, not "a directory exists"
    receipt('G2')
    assert alias.clean_workspace_current(root)
    receipt(None)
    assert not alias.clean_workspace_current(root)


def test_desktop_backend_checks_the_served_generation(root, tmp_path):
    packaging = REPO / 'ops' / 'desktop' / 'packaging'
    if str(packaging) not in sys.path:
        sys.path.insert(0, str(packaging))
    from desktop_backend import configure_melange_dashboard
    state = tmp_path / 'profile'
    state.mkdir()
    (root / 'Moneyball_Redesign.html').write_text('<!doctype html>', encoding='utf-8', newline='\n')
    (state / 'dashboard-selection.json').write_text(json.dumps(
        {'schemaVersion': 1, 'dataRoot': str(root.resolve()), 'dashboardFile': 'Moneyball_Redesign.html'}), encoding='utf-8')
    required = ('mlk-boot.js', 'app.css', 'ui-kit.css', 'forecasts.css', 'ui-kit.js', 'app.js', 'research.js', 'workspace.js')

    def full(out):
        for name in required:
            (out / name).write_bytes(b'/* generation */\n')
    module = SimpleNamespace(ASSETS=tmp_path / 'installed-assets')
    with pytest.raises(ValueError, match='missing a required local asset'):   # legacy approved/ lacks the required files
        configure_melange_dashboard(module, root, state)
    G.publish_generation(root, full, 'G1', log=quiet)
    assert configure_melange_dashboard(module, root, state) == 'Moneyball_Redesign.html'
    assert module.ASSETS == (root / 'fec' / 'surfaces' / 'staffer_live').resolve()


def test_builder_main_publishes_a_generation_and_never_writes_legacy(root, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_clean_workspace_generation_under_test',
                                                  FEC / 'surfaces' / 'build_clean_workspace.py')
    B = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(B)
    assert B.OUT is None                                                     # nothing names the legacy directory any more
    legacy = {p: p.read_bytes() for p in G.legacy_dir(root).rglob('*') if p.is_file()}
    seen = []

    def tiny_build(out, prior_dir=None):
        seen.append((out, prior_dir))
        writer('built')(out)
        return 3
    monkeypatch.setattr(B, 'ROOT', root)
    monkeypatch.setattr(B, 'build', tiny_build)
    B.main()
    pointer = G.read_pointer(root)
    out, prior = seen[0]
    assert out == G.generation_dir(root, pointer['generation']) and prior == G.legacy_dir(root)
    assert G.active_dir(root) == out and G.verify_generation(root, pointer['generation']) == []
    assert {p: p.read_bytes() for p in G.legacy_dir(root).rglob('*') if p.is_file()} == legacy
    assert (root / 'Moneyball_Redesign.html').read_bytes() == (B.SRC / 'index.html').read_bytes().replace(b'\n', b'\r\n')
