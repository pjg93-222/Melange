"""Current interactive Windows identity; never accepts a claimed user or password.

Authority is the process access token. WTS connection state and the input
desktop must both indicate a usable interactive session; lock, disconnection,
secure desktops and unavailable OS status never authorize opening the app.

https://learn.microsoft.com/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-openinputdesktop
https://learn.microsoft.com/windows/win32/api/wtsapi32/nf-wtsapi32-wtsquerysessioninformationw
"""
import ctypes
import json
import os
import re
import sys


class WindowsSessionError(RuntimeError):
    pass


def valid_session(value):
    return (isinstance(value, dict) and set(value) == {'schemaVersion', 'userSid', 'accountName', 'sessionId', 'locked'}
            and type(value['schemaVersion']) is int and value['schemaVersion'] == 1
            and isinstance(value['userSid'], str) and len(value['userSid']) <= 184
            and re.fullmatch(r'S-1-\d+(?:-\d+){1,15}', value['userSid']) is not None
            and value['userSid'] not in {'S-1-5-18', 'S-1-5-19', 'S-1-5-20'}
            and isinstance(value['accountName'], str) and 0 < len(value['accountName']) <= 256
            and not any(ord(char) < 32 or ord(char) == 127 for char in value['accountName'])
            and type(value['sessionId']) is int and 0 < value['sessionId'] < 0xffffffff
            and type(value['locked']) is bool)


class _Windows:
    def __init__(self):
        from ctypes import wintypes as w
        self.w = w
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True, winmode=0x800)
        self.advapi = ctypes.WinDLL('advapi32', use_last_error=True, winmode=0x800)
        self.user = ctypes.WinDLL('user32', use_last_error=True, winmode=0x800)
        self.wts = ctypes.WinDLL('wtsapi32', use_last_error=True, winmode=0x800)
        self.kernel.GetCurrentProcess.restype = w.HANDLE
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.LocalFree.argtypes = [ctypes.c_void_p]
        self.kernel.LocalFree.restype = ctypes.c_void_p
        self.advapi.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
        self.advapi.OpenProcessToken.restype = w.BOOL
        self.advapi.GetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
        self.advapi.GetTokenInformation.restype = w.BOOL
        self.advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(w.LPWSTR)]
        self.advapi.ConvertSidToStringSidW.restype = w.BOOL
        self.advapi.LookupAccountSidW.argtypes = [w.LPCWSTR, ctypes.c_void_p, w.LPWSTR, ctypes.POINTER(w.DWORD),
                                               w.LPWSTR, ctypes.POINTER(w.DWORD), ctypes.POINTER(ctypes.c_int)]
        self.advapi.LookupAccountSidW.restype = w.BOOL
        self.wts.WTSQuerySessionInformationW.argtypes = [w.HANDLE, w.DWORD, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.DWORD)]
        self.wts.WTSQuerySessionInformationW.restype = w.BOOL
        self.wts.WTSFreeMemory.argtypes = [ctypes.c_void_p]
        self.wts.WTSFreeMemory.restype = None
        self.user.OpenInputDesktop.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.user.OpenInputDesktop.restype = w.HANDLE
        self.user.CloseDesktop.argtypes = [w.HANDLE]
        self.user.GetUserObjectInformationW.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
        self.user.GetUserObjectInformationW.restype = w.BOOL

    def account_name(self, sid, fallback):
        name_size, domain_size, use = self.w.DWORD(), self.w.DWORD(), ctypes.c_int()
        self.advapi.LookupAccountSidW(None, sid, None, ctypes.byref(name_size), None, ctypes.byref(domain_size), ctypes.byref(use))
        if not 0 < name_size.value <= 1024 or domain_size.value > 1024:
            return fallback
        name = ctypes.create_unicode_buffer(name_size.value)
        domain = ctypes.create_unicode_buffer(max(1, domain_size.value))
        if not self.advapi.LookupAccountSidW(None, sid, name, ctypes.byref(name_size), domain, ctypes.byref(domain_size), ctypes.byref(use)):
            return fallback
        return (domain.value + '\\' if domain.value else '') + name.value

    def token_identity(self):
        token, length = self.w.HANDLE(), self.w.DWORD()
        if not self.advapi.OpenProcessToken(self.kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            raise WindowsSessionError('Windows sign-in is unavailable')
        try:
            self.advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(length))
            if not 0 < length.value <= 65536:
                raise WindowsSessionError('Windows sign-in is unavailable')
            raw = ctypes.create_string_buffer(length.value)
            if not self.advapi.GetTokenInformation(token, 1, raw, length.value, ctypes.byref(length)):
                raise WindowsSessionError('Windows sign-in is unavailable')
            sid = ctypes.cast(raw, ctypes.POINTER(ctypes.c_void_p))[0]
            text = self.w.LPWSTR()
            if not self.advapi.ConvertSidToStringSidW(sid, ctypes.byref(text)):
                raise WindowsSessionError('Windows sign-in is unavailable')
            try:
                user_sid = text.value
            finally:
                self.kernel.LocalFree(ctypes.cast(text, ctypes.c_void_p))
            session = self.w.DWORD()
            if not self.advapi.GetTokenInformation(token, 12, ctypes.byref(session), ctypes.sizeof(session), ctypes.byref(length)):
                raise WindowsSessionError('Windows sign-in is unavailable')
            return user_sid, self.account_name(sid, user_sid), session.value
        finally:
            self.kernel.CloseHandle(token)

    def session_active(self, session_id):
        pointer, size = ctypes.c_void_p(), self.w.DWORD()
        if not self.wts.WTSQuerySessionInformationW(None, session_id, 8, ctypes.byref(pointer), ctypes.byref(size)):
            return False
        try:
            return bool(pointer.value and size.value == ctypes.sizeof(ctypes.c_int)
                        and ctypes.cast(pointer, ctypes.POINTER(ctypes.c_int))[0] == 0)  # WTSActive
        finally:
            self.wts.WTSFreeMemory(pointer)

    def input_desktop_usable(self):
        desktop = self.user.OpenInputDesktop(0, False, 0x0001)  # DESKTOP_READOBJECTS; never switches desktops.
        if not desktop:
            return False
        try:
            name, needed = ctypes.create_unicode_buffer(256), self.w.DWORD()
            return bool(self.user.GetUserObjectInformationW(desktop, 2, name, ctypes.sizeof(name), ctypes.byref(needed))
                        and name.value.casefold() == 'default')
        finally:
            self.user.CloseDesktop(desktop)


def current_windows_identity():
    if os.name != 'nt':
        raise WindowsSessionError('Windows sign-in is required')
    api = _Windows()
    sid, account, session_id = api.token_identity()
    result = {'schemaVersion': 1, 'userSid': sid, 'accountName': account, 'sessionId': session_id,
              'locked': not (api.session_active(session_id) and api.input_desktop_usable())}
    if not valid_session(result):
        raise WindowsSessionError('Interactive Windows sign-in is required')
    return result


def main():
    try:
        raw = sys.stdin.buffer.read(1025)
        if len(raw) > 1024 or json.loads(raw) != {}:
            raise WindowsSessionError('A claimed Windows identity is not accepted')
        result = current_windows_identity()
    except Exception:
        print(json.dumps({'error': 'Windows sign-in is unavailable.'}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
