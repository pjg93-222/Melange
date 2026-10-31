"""Compiled full-workspace components and actual application bindings.

These objects are program capabilities, never decoded dataset objects. A
component authenticates immutable input material; its application binding must
independently verify actual consumer attachment and original-root preservation.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType

from module_application_contracts import DataIntakeBlocked, require
from module_data_snapshot import Snapshot, safe_root
from workspace_data_contract import WORKSPACE_KINDS, WORKSPACE_READERS


def validate_snapshot(snapshot):
    """Read-only full-workspace transport preflight, never installed health.

    The full factories separately validate analytics and attach actual native
    readers. This probe never creates cache/state or accepts a private path.
    """
    from workspace_archive import DomainArchive
    from workspace_data_contract import DASHBOARD_KIND, DISPLAY_GRAPH_KIND, ARCHIVE_MEMBERS
    require(type(snapshot) is Snapshot and snapshot.kind in WORKSPACE_KINDS[snapshot.app])
    if snapshot.kind == DASHBOARD_KIND:
        values={role:snapshot.json(role) for role in snapshot.roles}
        require(all(type(value) is dict for value in values.values()))
        require(type(values['members'].get('members')) is list
                and type(values['member-profiles'].get('members_heavy')) is list
                and len(values['members']['members'])==len(values['member-profiles']['members_heavy']))
    elif snapshot.kind == DISPLAY_GRAPH_KIND:
        from workspace_graph import VerifiedDisplayInput
        VerifiedDisplayInput(snapshot)
    else:
        for role in snapshot.roles:
            key=(snapshot.app,snapshot.kind,role)
            require(key in ARCHIVE_MEMBERS)
            with DomainArchive(snapshot.files[role],app_id=snapshot.app,kind=snapshot.kind,role=role,
                               expected_sha256=snapshot.objects[role]['sha256']) as archive:
                derivation=archive.json('derivation.json')
                members=derivation.get('members') if type(derivation) is dict else None
                require(type(members) is dict and set(members)==set(ARCHIVE_MEMBERS[key][0])-{'derivation.json'})
                for member,spec in members.items():
                    require(type(spec) is dict and set(spec)=={'sha256','bytes'}
                            and type(spec['bytes']) is int and spec['bytes']>=0
                            and spec['bytes']==archive.index[member][0].file_size
                            and type(spec['sha256']) is str and re.fullmatch('[0-9a-f]{64}',spec['sha256']))
                    value=hashlib.sha256()
                    for block in archive.chunks(member):value.update(block)
                    require(value.hexdigest()==spec['sha256'])


def _identity(info):
    return info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns


def _stamp(info):
    return (*_identity(info),info.st_ctime_ns)


def _data_require(value):
    if not value:raise DataIntakeBlocked('integrity')


class _Seal:
    def __init__(self,path,spec,is_cancelled):
        self.path,self.handle=Path(path),None
        try:
            self.named=self.path.lstat()
            _data_require(stat.S_ISREG(self.named.st_mode) and self.named.st_nlink==1
                    and not self.path.is_symlink()
                    and not getattr(self.named,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT)
            self.handle=self.path.open('rb');self.opened=os.fstat(self.handle.fileno())
            _data_require(_identity(self.named)==_identity(self.opened) and self.opened.st_size==spec['bytes'])
            digest=hashlib.sha256()
            for block in iter(lambda:self.handle.read(256*1024),b''):
                if is_cancelled():raise InterruptedError('Workspace input preparation was cancelled')
                digest.update(block)
            _data_require(digest.hexdigest()==spec['sha256'] and self.verify())
        except OSError:
            self.close();raise DataIntakeBlocked('storage') from None
        except Exception:
            self.close();raise

    def verify(self):
        try:
            return self.handle is not None and not self.handle.closed \
                and _stamp(self.path.lstat())==_stamp(self.named) \
                and _stamp(os.fstat(self.handle.fileno()))==_stamp(self.opened) \
                and _identity(self.path.lstat())==_identity(os.fstat(self.handle.fileno()))
        except OSError:return False

    def close(self):
        if self.handle is not None:self.handle.close()


def _content_class(app):
    if app=='melange':
        from workspace_melange import MelangeComponentContent
        return MelangeComponentContent
    require(app=='mentat')
    from workspace_mentat import MentatComponentContent
    return MentatComponentContent


def _bound_method(value,name):
    method=getattr(value,name,None)
    return callable(method) and getattr(method,'__self__',None) is value \
        and getattr(method,'__func__',None) is getattr(type(value),name,None)


class WorkspaceComponent:
    def __init__(self,snapshot,source,profile,program_fingerprint,content,*,is_cancelled=lambda:False):
        require(type(snapshot) is Snapshot and snapshot.app in WORKSPACE_KINDS
                and snapshot.kind in WORKSPACE_KINDS[snapshot.app] and type(source) is dict
                and source.get('appId')==snapshot.app and type(profile) is str
                and isinstance(program_fingerprint,str) and re.fullmatch('[0-9a-f]{64}',program_fingerprint)
                and type(content) is _content_class(snapshot.app)
                and _bound_method(content,'verify') and _bound_method(content,'close'))
        self.snapshot,self.source,self.profile=snapshot,MappingProxyType(dict(source)),safe_root(profile)
        self.program_fingerprint,self.content=program_fingerprint,content
        self._seals=[];self._closed=False
        try:
            for role,path in snapshot.files.items():self._seals.append(_Seal(path,snapshot.objects[role],is_cancelled))
            require(self.verify())
        except Exception:
            self.close();raise

    def verify(self):
        if self._closed:return False
        if not all(seal.verify() for seal in self._seals):raise DataIntakeBlocked('integrity')
        return _bound_method(self.content,'verify') and self.content.verify() is True

    def close(self):
        if self._closed:return
        self._closed=True
        try:self.content.close()
        finally:
            for seal in self._seals:seal.close()


def extract_archive(snapshot,profile,role,*,is_cancelled=lambda:False):
    require(type(snapshot) is Snapshot and snapshot.app in WORKSPACE_KINDS
            and snapshot.kind in WORKSPACE_KINDS[snapshot.app] and role in snapshot.files)
    from workspace_cache import prepare_cache
    return prepare_cache(profile_root=profile,app_id=snapshot.app,kind=snapshot.kind,role=role,
                         archive_path=snapshot.files[role],expected_sha256=snapshot.objects[role]['sha256'],
                         is_cancelled=is_cancelled)


def prepare_component(snapshot,*,source,profile,program_fingerprint,is_cancelled=lambda:False):
    require(type(snapshot) is Snapshot and snapshot.app in WORKSPACE_KINDS
            and snapshot.kind in WORKSPACE_KINDS[snapshot.app] and callable(is_cancelled)
            and not is_cancelled())
    if snapshot.app=='melange':
        from workspace_melange import prepare
    else:
        from workspace_mentat import prepare
    component=prepare(snapshot,source=source,profile=profile,program_fingerprint=program_fingerprint,
                      is_cancelled=is_cancelled)
    require(type(component) is WorkspaceComponent and component.snapshot is snapshot and component.verify())
    return {'appId':snapshot.app,'kind':snapshot.kind,'reader':component,
            'coverage':{'completeKind':True,'fullApplication':False}}


class WorkspaceBinding:
    def __init__(self,server,prepared,content):
        from module_data_handoff import PreparedHandoff
        require(type(prepared) is PreparedHandoff and prepared.contract.contract_id==prepared.contract.app_id+'.workspace.v1')
        self.server,self.prepared,self.content=server,prepared,content
        if prepared.contract.app_id=='melange':
            from workspace_melange import MelangeBinding
            require(type(content) is MelangeBinding)
        else:
            from workspace_mentat import MentatBinding
            require(type(content) is MentatBinding)
        require(_bound_method(content,'verify') and _bound_method(content,'handle_request'))
        self.components=tuple(value['reader'] for value in prepared.readers.values())
        require(len(self.components)==len(prepared.contract.required_kinds)
                and all(type(item) is WorkspaceComponent and item.program_fingerprint==prepared.contract.program_fingerprint
                        and item.snapshot.app==prepared.contract.app_id for item in self.components))
        require(not hasattr(server,'_desktop_workspace_binding'))
        server._desktop_workspace_binding=self
        require(self.verify())

    def verify(self):
        try:
            from module_data_handoff import recheck_original_roots
            recheck_original_roots(self.prepared)
            return getattr(self.server,'_desktop_workspace_binding',None) is self \
                and all(item.verify() for item in self.components) \
                and _bound_method(self.content,'verify') and self.content.verify() is True
        except DataIntakeBlocked:raise
        except (ValueError,OSError):return False

    def handle_request(self,handler):
        require(handler.server is self.server and self.verify() and _bound_method(self.content,'handle_request'))
        return self.content.handle_request(handler) is True


def _bind(server,prepared,app):
    require(prepared.contract.app_id==app and set(prepared.readers)==set(WORKSPACE_KINDS[app]))
    if app=='melange':
        from workspace_melange import bind
    else:
        from workspace_mentat import bind
    content=bind(server,prepared)
    binding=WorkspaceBinding(server,prepared,content)
    return {name:binding for name in WORKSPACE_READERS[app]}


def bind_melange_service(server,prepared):return _bind(server,prepared,'melange')
def bind_mentat_console(server,prepared):return _bind(server,prepared,'mentat')
