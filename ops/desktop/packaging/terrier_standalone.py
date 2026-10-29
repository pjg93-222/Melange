"""Local Terrier sessions behind the native launch-token boundary.

Password and explicit Windows-session modes never manufacture server grants or
impersonate legacy owners. Existing accounts, password hashes and roles remain.
"""
from ipaddress import ip_address
from pathlib import Path
from desktop_credentials import current_windows_identity, valid_session

MARKER = 'terrier.standalone.boundary'
_ISSUER = object()
WINDOWS_MARKER = 'terrier.standalone.windows'
_WINDOWS_ISSUER = object()
DISTRICTS = frozenset({'co-05', 'or-05', 'ct-01'})
MIDDLEWARE = 'terrier_standalone.StandaloneDesktopMiddleware'


def _direct(environment, origin):
    try:
        if not ip_address(environment.get('REMOTE_ADDR', '')).is_loopback:
            return False
    except ValueError:
        return False
    return (environment.get('HTTP_HOST') == origin.removeprefix('http://')
            and not any(environment.get(name) for name in (
                'HTTP_FORWARDED', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED_HOST', 'HTTP_X_FORWARDED_PROTO'))
            and environment.get('HTTP_ORIGIN', '') in ('', origin)
            and environment.get('HTTP_SEC_FETCH_SITE', '') in ('', 'same-origin', 'none'))


def configure_settings(*, windows_session=False):
    """Called by the explicit native standalone launcher before WSGI is built."""
    from django.conf import settings
    if settings.HOSTED or settings.DESKTOP_BOUNDARY or settings.LOCAL_ADMIN_ACCESS:
        raise ValueError('Standalone desktop requires explicit local authentication')
    stack = list(settings.MIDDLEWARE)
    anchor = 'server.research.middleware.LocalAdministratorMiddleware'
    if anchor not in stack or 'django.contrib.auth.middleware.AuthenticationMiddleware' not in stack:
        raise ValueError('Terrier local authentication middleware is unavailable')
    if MIDDLEWARE not in stack:
        # Run after the existing local middleware resets its request-only flag.
        stack.insert(stack.index(anchor) + 1, MIDDLEWARE)
    settings.MIDDLEWARE = stack
    settings.DESKTOP_STANDALONE = True
    settings.DESKTOP_WINDOWS_SESSION = bool(windows_session)


class StandaloneBoundary:
    """GuardedWSGI invokes this only after checking this launch's secret token."""
    def __init__(self, district, port, *, windows_account=None):
        if district not in DISTRICTS or type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Invalid standalone desktop boundary')
        self.district = district
        self.origin = 'http://127.0.0.1:' + str(port)
        self.windows_account = windows_account

    def authorize_environment(self, environment):
        from django.conf import settings
        environment.pop(MARKER, None)
        environment.pop(WINDOWS_MARKER, None)
        if (not getattr(settings, 'DESKTOP_STANDALONE', False) or settings.HOSTED
                or settings.DESKTOP_BOUNDARY or settings.LOCAL_ADMIN_ACCESS
                or self.district != settings.DISTRICT['id'] or not _direct(environment, self.origin)):
            return False
        if getattr(settings, 'DESKTOP_WINDOWS_SESSION', False):
            try:
                current = current_windows_identity()
                account = self.windows_account
                if (not valid_session(current) or current['locked'] or not isinstance(account, dict)
                        or account.get('userSid') != current['userSid'] or account.get('phase') != 'ready'):
                    return False
                environment[WINDOWS_MARKER] = (_WINDOWS_ISSUER, account['userId'], account['username'], current['accountName'])
            except Exception:
                return False
        elif self.windows_account is not None:
            return False
        environment[MARKER] = (_ISSUER, self.district, self.origin)
        return True


def _native_request(request):
    from django.conf import settings
    marker = request.META.get(MARKER)
    return (isinstance(marker, tuple) and len(marker) == 3 and marker[0] is _ISSUER
            and marker[1] == settings.DISTRICT['id'] and _direct(request.META, marker[2]))


def standalone_administrator_authorized(request):
    """Existing app capability issued by this launch's Windows boundary."""
    from django.conf import settings
    user = getattr(request, 'user', None)
    if (not getattr(settings, 'DESKTOP_STANDALONE', False)
            or not getattr(settings, 'DESKTOP_WINDOWS_SESSION', False)
            or settings.HOSTED or settings.DESKTOP_BOUNDARY or settings.LOCAL_ADMIN_ACCESS
            or getattr(request, 'local_admin_access', False) is not True
            or not user or not user.is_authenticated or not user.is_active or not user.is_staff
            or not _native_request(request)):
        return False
    marker = request.META.get(WINDOWS_MARKER)
    return bool(isinstance(marker, tuple) and len(marker) == 4
                and marker[0] is _WINDOWS_ISSUER and type(marker[1]) is int
                and user.pk == marker[1] and user.username == marker[2])


class StandaloneDesktopMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from django.http import JsonResponse
        from server.research.desktop_access import _login_asset
        if (not getattr(settings, 'DESKTOP_STANDALONE', False) or settings.HOSTED
                or settings.DESKTOP_BOUNDARY or settings.LOCAL_ADMIN_ACCESS or not _native_request(request)):
            return JsonResponse({'error': 'Local desktop authentication is required.'}, status=403)
        windows = getattr(settings, 'DESKTOP_WINDOWS_SESSION', False)
        if windows:
            from django.contrib.auth.models import User
            marker = request.META.get(WINDOWS_MARKER)
            if not (isinstance(marker, tuple) and len(marker) == 4 and marker[0] is _WINDOWS_ISSUER):
                return JsonResponse({'error': 'Windows sign-in is required.'}, status=403)
            user = User.objects.filter(pk=marker[1], username=marker[2], is_active=True).first()
            if user is None:
                return JsonResponse({'error': 'Windows account is unavailable.'}, status=403)
            # Only the current native Windows token supplies this account. Old
            # password cookies and renderer identity fields never select it.
            request.user = request._cached_user = user
            if request.method == 'POST' and request.path in ('/api/auth/login', '/api/auth/accept', '/api/auth/logout'):
                return JsonResponse({'error': 'Use your Windows sign-in to open or lock this desktop app.'}, status=403)
        user = getattr(request, 'user', None)
        signed_in = bool(user and user.is_authenticated and user.is_active)
        # These capabilities belong to an existing, signed-in staff account.
        # Never create an account, elevate its role, or skip its password here.
        request.local_admin_access = bool(signed_in and user.is_staff)
        auth = {'/api/auth/session': {'GET', 'HEAD'}, '/api/auth/login': {'POST'},
                '/api/auth/logout': {'POST'}, '/api/auth/accept': {'POST'}}
        if (request.method in auth.get(request.path, set()) or _login_asset(request)
                or request.path == '/api/health' and request.method in ('GET', 'HEAD')):
            response = self.get_response(request)
            if windows and request.path == '/api/auth/session' and response.status_code == 200 and not response.streaming:
                import json
                value = json.loads(response.content)
                value['authentication'] = 'windows'
                value['windowsAccountDisplayName'] = marker[3]
                response.content = json.dumps(value).encode('utf-8')
            # Login/first-password acceptance updates request.user inside the
            # view, after this middleware initially calculated its flag.
            if (request.method == 'POST' and request.path in ('/api/auth/login', '/api/auth/accept')
                    and response.status_code == 200 and not response.streaming):
                import json
                value = json.loads(response.content)
                if isinstance(value, dict) and 'authenticated' in value:
                    user = request.user
                    value['local_admin_access'] = bool(user.is_authenticated and user.is_active and user.is_staff)
                    response.content = json.dumps(value).encode('utf-8')
            return response
        if not signed_in:
            return JsonResponse({'error': 'Sign in to continue.'}, status=401)
        return self.get_response(request)


def prepare_accounts(state_root, *, legacy_owner=None):
    """Invite the first local owner; otherwise retain every existing account."""
    from django.conf import settings
    from django.contrib.auth.models import User
    from terrier_owner import first_owner_invitation, legacy_owner_invitation
    if (not getattr(settings, 'DESKTOP_STANDALONE', False) or settings.HOSTED
            or settings.DESKTOP_BOUNDARY or settings.LOCAL_ADMIN_ACCESS):
        raise ValueError('Standalone local account setup is unavailable')
    if legacy_owner:
        # Existing usable passwords are never reset. Ambiguous passwordless
        # account sets are refused by this already constrained migration helper.
        invitation = legacy_owner_invitation(Path(state_root), legacy_owner)
    elif not User.objects.exists():
        invitation = first_owner_invitation()
    else:
        invitation = None
    # Invitation secrets stay in the native health reply and browser fragment.
    return '/#invite=' + invitation.partition('=')[2] if invitation else None


def prepare_windows_account(state_root):
    """Bind one real local account to the OS user and copy local saved views once.

    A protected pending record precedes a single SQLite transaction. The account,
    view copies and recovery marker commit together; a crash before the final
    protected write resumes from that marker instead of creating duplicates.
    """
    import hashlib
    import json
    import uuid
    import native_access_state as protected
    from django.conf import settings
    from django.contrib.auth.models import User
    from django.db import connection
    from server.research.models import SavedView
    if (not getattr(settings, 'DESKTOP_STANDALONE', False) or not getattr(settings, 'DESKTOP_WINDOWS_SESSION', False)
            or settings.HOSTED or settings.DESKTOP_BOUNDARY or settings.LOCAL_ADMIN_ACCESS
            or connection.vendor != 'sqlite' or connection.in_atomic_block):
        raise ValueError('Windows local account setup is unavailable')
    current = current_windows_identity()
    if not valid_session(current) or current['locked']:
        raise ValueError('Unlock your Windows session to open the app')
    root = Path(state_root).resolve(strict=True)
    if Path(connection.settings_dict['NAME']).resolve().parent != root:
        raise ValueError('Windows account requires the selected local state directory')
    sid = current['userSid']
    username = 'windows_' + hashlib.sha256(sid.encode('utf-8')).hexdigest()[:40]
    base_keys = {'schemaVersion', 'purpose', 'phase', 'bindingId', 'userSid', 'username'}
    with connection.cursor() as cursor:
        cursor.execute('BEGIN IMMEDIATE')
        try:
            cursor.execute('CREATE TABLE IF NOT EXISTS desktop_windows_local_binding ('
                           'binding_id TEXT PRIMARY KEY, user_sid TEXT NOT NULL, user_id INTEGER NOT NULL, '
                           'username TEXT NOT NULL, saved_views TEXT NOT NULL)')
            record = protected.read(root, 'windows-account')
            if record is None:
                record = {'schemaVersion': 1, 'purpose': 'desktop-windows-account', 'phase': 'pending',
                          'bindingId': str(uuid.uuid4()), 'userSid': sid, 'username': username}
                protected.write(root, 'windows-account', record)
            if (not isinstance(record, dict) or type(record.get('schemaVersion')) is not int or record.get('schemaVersion') != 1
                    or record.get('purpose') != 'desktop-windows-account' or record.get('userSid') != sid
                    or record.get('username') != username or record.get('phase') not in ('pending', 'ready')
                    or set(record) != base_keys | ({'userId', 'savedViews'} if record.get('phase') == 'ready' else set())
                    or str(uuid.UUID(record['bindingId'])) != record['bindingId']):
                raise ValueError('Windows account binding is invalid')
            cursor.execute('SELECT user_sid,user_id,username,saved_views FROM desktop_windows_local_binding WHERE binding_id=%s', [record['bindingId']])
            stored = cursor.fetchone()
            if stored is None:
                if record['phase'] != 'pending' or User.objects.filter(username=username).exists():
                    raise ValueError('Windows account cannot claim an existing local account')
                # Preserve every old account, including passwords, roles and IDs.
                user = User(username=username, is_active=True, is_staff=True, is_superuser=False)
                user.set_unusable_password()
                user.save()
                copied = []
                for view in SavedView.objects.exclude(owner_id=user.pk).order_by('pk').iterator():
                    clone = SavedView.objects.create(owner=user, name=view.name, config=view.config)
                    copied.append({'sourceId': view.pk, 'copyId': clone.pk})
                cursor.execute('INSERT INTO desktop_windows_local_binding(binding_id,user_sid,user_id,username,saved_views) VALUES(%s,%s,%s,%s,%s)',
                               [record['bindingId'], sid, user.pk, username, json.dumps(copied, separators=(',', ':'))])
            else:
                if stored[0] != sid or stored[2] != username:
                    raise ValueError('Windows local account marker is invalid')
                user = User.objects.filter(pk=stored[1], username=username).first()
                copied = json.loads(stored[3])
                if user is None or not isinstance(copied, list) or any(not isinstance(row, dict) or set(row) != {'sourceId', 'copyId'}
                        or type(row['sourceId']) is not int or type(row['copyId']) is not int or min(row.values()) <= 0 for row in copied):
                    raise ValueError('Windows local account recovery is invalid')
            ready = {**record, 'phase': 'ready', 'userId': user.pk, 'savedViews': copied}
            if record['phase'] == 'ready' and record != ready:
                raise ValueError('Windows account binding changed')
            if len(json.dumps(ready).encode('utf-8')) > protected.MAX_VALUE:
                raise ValueError('Windows local account mapping is too large')
            if not user.is_active or not user.is_staff or user.is_superuser:
                raise ValueError('Windows local account is disabled or its role changed')
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    if record != ready:
        protected.write(root, 'windows-account', ready)
    return ready
