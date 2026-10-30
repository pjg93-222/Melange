"""Bounded dual native capability. Legacy public input framing is unchanged."""
from dataclasses import dataclass
import io
import os
import struct

from module_application_contracts import (ApplicationContract, ModuleInputError, DataIntakeBlocked,
    application_contract, canonical, require, verify_program)
from module_data_handoff import close_handoff, prepare_handoff, read_frame, _parse


@dataclass(frozen=True, eq=False)
class PreparedWorkspace:
    public: object
    workspace: object


def _frame(value):
    raw = canonical(value)
    return io.BytesIO(struct.pack('>I', len(raw)) + raw)


def prepare_workspace_handoff(stream, *, app_id, **options):
    """Both independently verified inputs must name this same native launch.

    Context equality is checked before either reader factory runs. Each frame
    then retains its own signed manifest, protected channel state and cache.
    The caller's compiled contract lookup, never downloaded selectors, chooses
    its factories and installed-program closure.
    """
    public = workspace = None
    contracts = None
    try:
        value = _parse(read_frame(stream, timeout=options.get('timeout', 5.0),
                                  is_cancelled=options.get('is_cancelled', lambda: False)))
        require(type(value) is dict and set(value) == {'schemaVersion', 'publicInput', 'workspaceInput'}
                and type(value['schemaVersion']) is int and value['schemaVersion'] == 1
                and app_id in ('melange', 'mentat'))
        first, second = value['publicInput'], value['workspaceInput']
        require(type(first) is dict and type(second) is dict)
        allowed_public = {app_id + '.public-data.v1'}
        if app_id == 'melange':
            allowed_public.add('melange.public-data.pages.v1')
        require(first.get('contractId') in allowed_public and second.get('contractId') == app_id + '.workspace.v1')
        shared = ('schemaVersion', 'appId', 'profileRoot', 'sourceRoot', 'originalDataRoot',
                  'stateRoot', 'launchNonce', 'programFingerprint')
        require(all(key in first and key in second and type(first[key]) is type(second[key])
                    and first[key] == second[key] for key in shared)
                and first['appId'] == app_id)
        require(type(first.get('source')) is dict and type(second.get('source')) is dict)
        roots = [item['source'].get('cacheRoot') for item in (first, second)]
        require(all(type(root) is str and os.path.isabs(root) for root in roots)
                and os.path.normcase(os.path.abspath(roots[0])) != os.path.normcase(os.path.abspath(roots[1])))
        lookup = options.get('lookup') or application_contract
        contracts = []
        for message in (first, second):
            contract = lookup(app_id, message['contractId'])
            require(type(contract) is ApplicationContract and contract.app_id == app_id
                    and contract.contract_id == message['contractId']
                    and contract.program_fingerprint == message['programFingerprint'])
            verify_program(contract, source_root=options['source_root'], bootstrap_root=options['bootstrap_root'])
            contracts.append(contract)
        public = prepare_handoff(_frame(first), app_id=app_id, **options)
        workspace = prepare_handoff(_frame(second), app_id=app_id, **options)
        require(public.roots == workspace.roots and public.launch_nonce == workspace.launch_nonce
                and public.contract.program_fingerprint == workspace.contract.program_fingerprint)
        return PreparedWorkspace(public, workspace)
    except Exception as error:
        for prepared in (workspace, public):
            if prepared is not None:
                try:
                    close_handoff(prepared)
                except Exception:
                    pass
        if type(error) is DataIntakeBlocked and error.native_status is not None and contracts is not None and len(contracts) == 2:
            for contract in contracts:
                verify_program(contract, source_root=options['source_root'], bootstrap_root=options['bootstrap_root'])
            error.native_status = {**error.native_status, 'sourceDigests': {
                'public': first['source']['manifestSha256'], 'workspace': second['source']['manifestSha256']}}
            raise
        raise ModuleInputError() from None


def close_workspace_handoff(prepared):
    require(type(prepared) is PreparedWorkspace)
    try:
        close_handoff(prepared.workspace)
    finally:
        close_handoff(prepared.public)


def emit_workspace_data_blocked(error, prepared, stream):
    """Bind a known late data failure only to this still-verified dual launch."""
    if type(error) is not DataIntakeBlocked:
        return False
    from module_data_handoff import PreparedHandoff, recheck_original_roots, emit_data_blocked, _root
    require(type(prepared) is PreparedWorkspace
            and type(prepared.public) is PreparedHandoff and type(prepared.workspace) is PreparedHandoff)
    public, workspace = prepared.public, prepared.workspace
    require(public.contract.app_id == workspace.contract.app_id
            and workspace.contract.contract_id == public.contract.app_id + '.workspace.v1'
            and public.roots == workspace.roots and public.launch_nonce == workspace.launch_nonce
            and public.contract.program_fingerprint == workspace.contract.program_fingerprint)
    require(_root(public.roots['profileRoot']) == os.path.normcase(os.path.abspath(public.roots['profileRoot'])))
    for item in (public, workspace):
        recheck_original_roots(item)
        verify_program(item.contract, source_root=item.roots['sourceRoot'], bootstrap_root=item.bootstrap_root)
    error.native_status = {'schemaVersion': 1, 'appId': public.contract.app_id,
        'launchNonce': public.launch_nonce, 'programFingerprint': public.contract.program_fingerprint,
        'sourceDigests': {'public': public.source['manifestSha256'], 'workspace': workspace.source['manifestSha256']},
        'reason': error.reason}
    return emit_data_blocked(error, stream)


def abort_workspace_data_blocked(error, public, workspace):
    """A known HTTP-thread data failure must not become a binary timeout."""
    import sys
    if not emit_workspace_data_blocked(error, PreparedWorkspace(public, workspace), sys.stdout):
        raise error
    os._exit(1)
