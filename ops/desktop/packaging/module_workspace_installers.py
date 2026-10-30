"""Fixed workspace consumers installed into the actual native-owned server.

The transport's complete-kind claim is not application health. Only these
compiled binders can install consumers, preserve the native original roots,
and attest the actual server after the independent public installation.
"""
from types import MappingProxyType
import weakref

from module_application_contracts import application_contract, require
from module_data_handoff import (InstalledInputs, PlannedOriginalRoot,
    PreparedHandoff, recheck_original_roots)
from workspace_data_contract import (WORKSPACE_KINDS, WORKSPACE_READERS,
    WORKSPACE_PRIVATE_BOUNDARIES)


def prepare_workspace_readers(**options):
    app = options.get('app_id')
    require(app in WORKSPACE_KINDS and tuple(options.get('required_kinds', ())) == WORKSPACE_KINDS[app]
            and 'workspace' not in options and 'reader_registry' not in options)
    contract = application_contract(app, app + '.workspace.v1')
    require(contract is not None)
    from module_data_launch import prepare_module_readers
    from module_workspace_inputs import prepare_component
    def prepare(snapshot, *, source, is_cancelled):
        return prepare_component(snapshot, source=source, profile=options['profile'],
            program_fingerprint=contract.program_fingerprint, is_cancelled=is_cancelled)
    return prepare_module_readers(**options, workspace=True,
        reader_registry={kind: prepare for kind in WORKSPACE_KINDS[app]})


_CAPTURED = weakref.WeakKeyDictionary()
_INSTALLED = weakref.WeakKeyDictionary()


def _method(value, owner, name):
    method = getattr(value, name, None)
    require(type(value) is owner and getattr(method, '__self__', None) is value
            and getattr(method, '__func__', None) is getattr(owner, name))
    return method


def workspace_components(prepared):
    from module_workspace_inputs import WorkspaceComponent
    require(type(prepared) is PreparedHandoff)
    app = prepared.contract.app_id
    require(app in WORKSPACE_KINDS and prepared.contract.contract_id == app + '.workspace.v1'
            and prepared.contract.required_kinds == WORKSPACE_KINDS[app]
            and set(prepared.readers) == set(WORKSPACE_KINDS[app]))
    components = []
    for kind in WORKSPACE_KINDS[app]:
        bound = prepared.readers[kind]
        require(type(bound) is dict and set(bound) == {'appId', 'kind', 'reader', 'coverage'}
                and bound['appId'] == app and bound['kind'] == kind
                and type(bound['coverage']) is dict
                and set(bound['coverage']) == {'completeKind', 'fullApplication'}
                and bound['coverage']['completeKind'] is True
                and bound['coverage']['fullApplication'] is False)
        component = bound['reader']
        _method(component, WorkspaceComponent, 'close')
        require(_method(component, WorkspaceComponent, 'verify')() is True)
        components.append(component)
    return tuple(components)


def capture_workspace_originals(prepared, server):
    require(type(prepared) is PreparedHandoff and server is not None and prepared not in _CAPTURED
            and prepared.contract.private_boundaries == WORKSPACE_PRIVATE_BOUNDARIES[prepared.contract.app_id]
            and len(prepared.original_root_plans) == 2
            and all(type(plan) is PlannedOriginalRoot for plan in prepared.original_root_plans))
    recheck_original_roots(prepared)
    plans = prepared.original_root_plans
    require(tuple(plan.original for plan in plans) ==
            (prepared.roots['originalDataRoot'], prepared.roots['stateRoot']))
    originals = dict(zip(prepared.contract.private_boundaries, plans))
    _CAPTURED[prepared] = (server, originals)
    return dict(originals)


def install_workspace_readers(prepared, server, originals):
    from module_workspace_inputs import (WorkspaceBinding, bind_melange_service,
        bind_mentat_console)
    require(type(prepared) is PreparedHandoff and prepared in _CAPTURED and prepared not in _INSTALLED
            and type(originals) is MappingProxyType)
    actual_server, captured = _CAPTURED[prepared]
    require(server is actual_server and set(originals) == set(captured)
            and all(originals[key] is captured[key] for key in captured))
    components = workspace_components(prepared)
    bind = bind_melange_service if prepared.contract.app_id == 'melange' else bind_mentat_console
    readers = bind(server, prepared)
    require(type(readers) is dict and set(readers) == set(WORKSPACE_READERS[prepared.contract.app_id]))
    # A single sealed binding owns all fixed logical consumers and routes. It
    # verifies their actual attachment; downloaded JSON never supplies methods.
    binding = next(iter(readers.values()))
    require(all(value is binding for value in readers.values()))
    _method(binding, WorkspaceBinding, 'handle_request')
    def verify():
        recheck_original_roots(prepared)
        current = workspace_components(prepared)
        require(len(current) == len(components) and all(left is right for left, right in zip(current, components))
                and all(originals[key] is captured[key] for key in captured)
                and _method(binding, WorkspaceBinding, 'verify')() is True)
        return True
    require(verify() is True)
    _INSTALLED[prepared] = (server, binding, verify)
    return InstalledInputs(server, dict(readers), dict(originals), verify)


def handle_workspace_request(handler, prepared):
    """Called only after the native HTTP owner/session guard and health seal."""
    from module_workspace_inputs import WorkspaceBinding
    require(type(prepared) is PreparedHandoff and prepared in _INSTALLED)
    server, binding, verify = _INSTALLED[prepared]
    require(handler.server is server and verify() is True)
    result = _method(binding, WorkspaceBinding, 'handle_request')(handler)
    require(type(result) is bool)
    return result
