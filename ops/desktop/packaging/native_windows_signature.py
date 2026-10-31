"""Fixed read-only Authenticode probe; no shell, certificate import or command input.

Layouts follow Microsoft's wintrust.h/wincrypt.h documentation. The result is
only a publisher verdict; the caller still authenticates the complete package
against its signed release manifest before AND after this probe.
"""
import ctypes
from ctypes import wintypes as W
import json
import os
import sys

PINNED = '0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'
UNTRUSTED_ROOT = 0x800B0109
UNTRUSTED_ROOT_BIT = 0x20


class GUID(ctypes.Structure):
    _fields_ = [('Data1', W.DWORD), ('Data2', W.WORD), ('Data3', W.WORD), ('Data4', W.BYTE * 8)]


class FILE_INFO(ctypes.Structure):
    _fields_ = [('cbStruct', W.DWORD), ('pcwszFilePath', W.LPCWSTR),
                ('hFile', W.HANDLE), ('pgKnownSubject', ctypes.c_void_p)]


class TRUST_DATA(ctypes.Structure):
    _fields_ = [('cbStruct', W.DWORD), ('pPolicyCallbackData', ctypes.c_void_p),
                ('pSIPClientData', ctypes.c_void_p), ('dwUIChoice', W.DWORD),
                ('fdwRevocationChecks', W.DWORD), ('dwUnionChoice', W.DWORD),
                ('pFile', ctypes.POINTER(FILE_INFO)), ('dwStateAction', W.DWORD),
                ('hWVTStateData', W.HANDLE), ('pwszURLReference', W.LPWSTR),
                ('dwProvFlags', W.DWORD), ('dwUIContext', W.DWORD),
                ('pSignatureSettings', ctypes.c_void_p)]


class CERT_CONTEXT(ctypes.Structure):
    _fields_ = [('dwCertEncodingType', W.DWORD), ('pbCertEncoded', ctypes.c_void_p),
                ('cbCertEncoded', W.DWORD), ('pCertInfo', ctypes.c_void_p),
                ('hCertStore', W.HANDLE)]


class TRUST_STATUS(ctypes.Structure):
    _fields_ = [('dwErrorStatus', W.DWORD), ('dwInfoStatus', W.DWORD)]


class CHAIN_PREFIX(ctypes.Structure):
    _fields_ = [('cbSize', W.DWORD), ('TrustStatus', TRUST_STATUS)]


class PROVIDER_CERT(ctypes.Structure):
    _fields_ = [('cbStruct', W.DWORD), ('pCert', ctypes.POINTER(CERT_CONTEXT)),
                ('fCommercial', W.BOOL), ('fTrustedRoot', W.BOOL),
                ('fSelfSigned', W.BOOL), ('fTestCert', W.BOOL),
                ('dwRevokedReason', W.DWORD), ('dwConfidence', W.DWORD),
                ('dwError', W.DWORD), ('pTrustListContext', ctypes.c_void_p),
                ('fTrustListSignerCert', W.BOOL), ('pCtlContext', ctypes.c_void_p),
                ('dwCtlError', W.DWORD), ('fIsCyclic', W.BOOL),
                ('pChainElement', ctypes.c_void_p)]


class PROVIDER_SIGNER(ctypes.Structure):
    _fields_ = [('cbStruct', W.DWORD), ('sftVerifyAsOf', W.FILETIME),
                ('csCertChain', W.DWORD), ('pasCertChain', ctypes.POINTER(PROVIDER_CERT)),
                ('dwSignerType', W.DWORD), ('psSigner', ctypes.c_void_p),
                ('dwError', W.DWORD), ('csCounterSigners', W.DWORD),
                ('pasCounterSigners', ctypes.c_void_p),
                ('pChainContext', ctypes.POINTER(CHAIN_PREFIX))]


def _api(dll, name, args, result):
    function = getattr(dll, name)
    function.argtypes, function.restype = args, result
    return function


def accepted(result):
    """Only Windows success or the pinned self-signed root exception."""
    if result['thumbprint'] != PINNED:
        return False
    # WinVerifyTrust's exact zero is the Windows trust verdict, including its
    # timestamp policy. Auxiliary chain diagnostics cannot overturn success.
    if result['wintrustStatus'] == 0:
        return True
    if (not result['validAtVerificationTime']
            or result['counterSignerErrors'] or result['certificateError'] not in (0, UNTRUSTED_ROOT)
            or result['signerError'] not in (0, UNTRUSTED_ROOT)
            or result['chainErrors'] & ~UNTRUSTED_ROOT_BIT):
        return False
    return (result['wintrustStatus'] == UNTRUSTED_ROOT and result['selfSigned']
            and result['chainErrors'] == UNTRUSTED_ROOT_BIT)


def signature(filename):
    if os.name != 'nt' or type(filename) is not str or not os.path.isabs(filename) or '\0' in filename:
        raise ValueError('Invalid Windows signature request')
    filename = os.path.abspath(filename)
    # LOAD_LIBRARY_SEARCH_SYSTEM32 prevents a DLL beside the app or in PATH from
    # impersonating the Windows verifier. No trust store is opened for writing.
    kernel = ctypes.WinDLL('kernel32.dll', use_last_error=True, winmode=0x800)
    trust = ctypes.WinDLL('wintrust.dll', use_last_error=True, winmode=0x800)
    crypto = ctypes.WinDLL('crypt32.dll', use_last_error=True, winmode=0x800)
    create = _api(kernel, 'CreateFileW', [W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p, W.DWORD, W.DWORD, W.HANDLE], W.HANDLE)
    close = _api(kernel, 'CloseHandle', [W.HANDLE], W.BOOL)
    verify = _api(trust, 'WinVerifyTrust', [W.HWND, ctypes.POINTER(GUID), ctypes.POINTER(TRUST_DATA)], W.LONG)
    provider = _api(trust, 'WTHelperProvDataFromStateData', [W.HANDLE], ctypes.c_void_p)
    signer_api = _api(trust, 'WTHelperGetProvSignerFromChain', [ctypes.c_void_p, W.DWORD, W.BOOL, W.DWORD], ctypes.POINTER(PROVIDER_SIGNER))
    cert_api = _api(trust, 'WTHelperGetProvCertFromChain', [ctypes.POINTER(PROVIDER_SIGNER), W.DWORD], ctypes.POINTER(PROVIDER_CERT))
    property_api = _api(crypto, 'CertGetCertificateContextProperty', [ctypes.POINTER(CERT_CONTEXT), W.DWORD, ctypes.c_void_p, ctypes.POINTER(W.DWORD)], W.BOOL)
    validity = _api(crypto, 'CertVerifyTimeValidity', [ctypes.POINTER(W.FILETIME), ctypes.c_void_p], W.LONG)
    handle = create(filename, 0x80000000, 1, None, 3, 0x80, None)  # read, share-read only, existing
    if handle in (None, ctypes.c_void_p(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    action = GUID(0x00AAC56B, 0xCD44, 0x11D0, (W.BYTE * 8)(0x8C, 0xC2, 0, 0xC0, 0x4F, 0xC2, 0x95, 0xEE))
    info = FILE_INFO(ctypes.sizeof(FILE_INFO), filename, handle, None)
    data = TRUST_DATA()
    data.cbStruct, data.dwUIChoice, data.dwUnionChoice = ctypes.sizeof(data), 2, 1
    data.pFile, data.dwStateAction = ctypes.pointer(info), 1
    # Check cached revocation for the chain except the root. No network, UI or
    # lifetime-signing override: Windows validates a legitimate timestamp.
    data.dwProvFlags = 0x80 | 0x1000 | 0x2000
    result = dict(schemaVersion=1, path=filename, wintrustStatus=0, thumbprint=None,
                  selfSigned=False, validAtVerificationTime=False, signerError=None,
                  certificateError=None, chainErrors=0xFFFFFFFF, counterSignerErrors=True)
    try:
        result['wintrustStatus'] = verify(None, ctypes.byref(action), ctypes.byref(data)) & 0xFFFFFFFF
        state = provider(data.hWVTStateData) if data.hWVTStateData else None
        signer = signer_api(state, 0, False, 0) if state else None
        cert = cert_api(signer, 0) if signer else None
        if result['wintrustStatus'] in (0, UNTRUSTED_ROOT) and not (cert and cert.contents.pCert and signer.contents.pChainContext):
            raise ValueError('Windows signature verdict is incomplete')
        if cert and cert.contents.pCert and signer.contents.pChainContext:
            s, c = signer.contents, cert.contents
            if s.cbStruct < ctypes.sizeof(PROVIDER_SIGNER) or c.cbStruct < ctypes.sizeof(PROVIDER_CERT):
                raise ValueError('Unsupported Windows trust provider layout')
            size, digest = W.DWORD(20), (W.BYTE * 20)()
            if not property_api(c.pCert, 3, digest, ctypes.byref(size)) or size.value != 20:
                raise ValueError('Windows signer fingerprint unavailable')
            result.update(thumbprint=bytes(digest).hex().upper(), selfSigned=bool(c.fSelfSigned),
                          validAtVerificationTime=validity(ctypes.byref(s.sftVerifyAsOf), c.pCert.contents.pCertInfo) == 0,
                          signerError=int(s.dwError), certificateError=int(c.dwError),
                          chainErrors=int(s.pChainContext.contents.TrustStatus.dwErrorStatus),
                          counterSignerErrors=False)
            if s.csCounterSigners > 8:
                raise ValueError('Too many signature countersigners')
            for index in range(s.csCounterSigners):
                counter = signer_api(state, 0, True, index)
                if (not counter or counter.contents.dwError or not counter.contents.pChainContext
                        or counter.contents.pChainContext.contents.TrustStatus.dwErrorStatus):
                    result['counterSignerErrors'] = True
        result['verdict'] = 'verified' if accepted(result) else 'refused'
        return result
    finally:
        data.dwStateAction = 2
        verify(None, ctypes.byref(action), ctypes.byref(data))
        close(handle)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate field')
        result[key] = value
    return result


def installer_processes(request):
    """Observe only matching installer instances; this never authorizes a launch."""
    import datetime
    import re
    import _wmi
    if (os.name != 'nt' or type(request) is not dict or set(request) != {'installerPath', 'token'}
            or type(request['installerPath']) is not str or not os.path.isabs(request['installerPath'])
            or '\0' in request['installerPath'] or type(request['token']) is not str
            or re.fullmatch(r'[0-9a-f]{64}', request['token']) is None):
        raise ValueError('Invalid installer observation request')
    expected = os.path.normcase(os.path.abspath(request['installerPath']))
    token = '--desktop-activation=' + request['token']
    kernel = ctypes.WinDLL('kernel32.dll', use_last_error=True, winmode=0x800)
    shell = ctypes.WinDLL('shell32.dll', use_last_error=True, winmode=0x800)

    class PROCESS_ENTRY(ctypes.Structure):
        _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD), ('th32ProcessID', W.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', W.DWORD),
                    ('cntThreads', W.DWORD), ('th32ParentProcessID', W.DWORD),
                    ('pcPriClassBase', W.LONG), ('dwFlags', W.DWORD), ('szExeFile', W.WCHAR * 260)]

    snapshot = _api(kernel, 'CreateToolhelp32Snapshot', [W.DWORD, W.DWORD], W.HANDLE)
    first = _api(kernel, 'Process32FirstW', [W.HANDLE, ctypes.POINTER(PROCESS_ENTRY)], W.BOOL)
    next_process = _api(kernel, 'Process32NextW', [W.HANDLE, ctypes.POINTER(PROCESS_ENTRY)], W.BOOL)
    open_process = _api(kernel, 'OpenProcess', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
    image = _api(kernel, 'QueryFullProcessImageNameW', [W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)], W.BOOL)
    times = _api(kernel, 'GetProcessTimes', [W.HANDLE, *([ctypes.POINTER(W.FILETIME)] * 4)], W.BOOL)
    close = _api(kernel, 'CloseHandle', [W.HANDLE], W.BOOL)
    parse_args = _api(shell, 'CommandLineToArgvW', [W.LPCWSTR, ctypes.POINTER(ctypes.c_int)], ctypes.POINTER(W.LPWSTR))
    free = _api(kernel, 'LocalFree', [ctypes.c_void_p], ctypes.c_void_p)
    handle = snapshot(2, 0)
    if handle in (None, ctypes.c_void_p(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    result = []
    try:
        entry = PROCESS_ENTRY()
        entry.dwSize = ctypes.sizeof(entry)
        found = first(handle, ctypes.byref(entry))
        while found:
            pid = int(entry.th32ProcessID)
            process = open_process(0x1000, False, pid)  # limited query only, never debug/elevate
            if process:
                try:
                    capacity, executable = W.DWORD(32768), ctypes.create_unicode_buffer(32768)
                    if image(process, 0, executable, ctypes.byref(capacity)) and os.path.normcase(os.path.abspath(executable.value)) == expected:
                        created, exited, system, user = (W.FILETIME() for _ in range(4))
                        if not times(process, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(system), ctypes.byref(user)):
                            raise ctypes.WinError(ctypes.get_last_error())
                        # Only a validated OS-observed integer is formatted into
                        # this fixed query; no path, token or user WQL is used.
                        raw = _wmi.exec_query('SELECT CommandLine,CreationDate FROM Win32_Process WHERE ProcessId=' + str(pid))
                        if len(raw) > 8192:
                            raise ValueError('Installer observation too large')
                        values = _object(part.split('=', 1) for part in raw.split('\0') if part)
                        if not values:  # exited after the held process handle was opened
                            found = next_process(handle, ctypes.byref(entry))
                            continue
                        if set(values) != {'CommandLine', 'CreationDate'}:
                            raise ValueError('Incomplete installer observation')
                        stamp = values['CreationDate']
                        if re.fullmatch(r'\d{14}\.\d{6}[+-]\d{3}', stamp) is None:
                            raise ValueError('Invalid process creation time')
                        offset = int(stamp[22:]) * (1 if stamp[21] == '+' else -1)
                        date = datetime.datetime.strptime(stamp[:21], '%Y%m%d%H%M%S.%f').replace(
                            tzinfo=datetime.timezone(datetime.timedelta(minutes=offset))).astimezone(datetime.timezone.utc)
                        filetime = (created.dwHighDateTime << 32) | created.dwLowDateTime
                        actual = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(microseconds=filetime // 10)
                        if abs((date - actual).total_seconds()) > 0.001:
                            raise ValueError('Process identity changed during observation')
                        count = ctypes.c_int()
                        arguments = parse_args(values['CommandLine'], ctypes.byref(count))
                        if not arguments:
                            raise ValueError('Process arguments unavailable')
                        try:
                            matches = sum(arguments[index] == token for index in range(count.value))
                        finally:
                            free(arguments)
                        if matches == 1:
                            result.append({'pid': pid, 'startedAt': date.isoformat(), 'installerPath': executable.value})
                            if len(result) > 8:
                                raise ValueError('Too many installer instances')
                finally:
                    close(process)
            found = next_process(handle, ctypes.byref(entry))
        return result
    finally:
        close(handle)


def main():
    try:
        if sys.argv[1:] not in (['--desktop-windows-signature'], ['--desktop-installer-processes']):
            raise ValueError('Only the fixed signature probe mode is supported')
        raw = sys.stdin.buffer.read(65537)
        request = json.loads(raw, object_pairs_hook=_object)
        if len(raw) > 65536 or type(request) is not dict:
            raise ValueError('Invalid signature request')
        if sys.argv[1:] == ['--desktop-installer-processes']:
            result = installer_processes(request)
        else:
            if set(request) != {'path'}:
                raise ValueError('Invalid signature request')
            result = signature(request['path'])
    except Exception:
        print(json.dumps({'error': 'Windows signature verification unavailable.'}))
        return 1
    print(json.dumps(result, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
