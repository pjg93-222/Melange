"""Local Terrier password sessions behind the native launch-token boundary.

Standalone is a separate local mode, never a server grant or a passwordless
owner. Existing Django account IDs, password hashes and roles are preserved.
"""
from ipaddress import ip_address
from pathlib import Path

MARKER = 'terrier.standalone.boundary'
_ISSUER = object()
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


def configure_settings():
    """Called by the explicit native standalone launcher before WSGI is built."""
    from django.conf import settings
    if settings.HOSTED or settings.DESKTOP_BOUNDARY or settings.LOCAL_ADMIN_ACCESS:
        raise ValueError('Standalone desktop requires local password authentication')
    stack = list(settings.MIDDLEWARE)
    anchor = 'server.research.middleware.LocalAdministratorMiddleware'
    if anchor not in stack or 'django.contrib.auth.middleware.AuthenticationMiddleware' not in stack:
        raise ValueError('Terrier local authentication middleware is unavailable')
    if MIDDLEWARE not in stack:
        # Run after the existing local middleware resets its request-only flag.
        stack.insert(stack.index(anchor) + 1, MIDDLEWARE)
    settings.MIDDLEWARE = stack
    settings.DESKTOP_STANDALONE = True


class StandaloneBoundary:
    """GuardedWSGI invokes this only after checking this launch's secret token."""
    def __init__(self, district, port):
        if district not in DISTRICTS or type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Invalid standalone desktop boundary')
        self.district = district
        self.origin = 'http://127.0.0.1:' + str(port)

    def authorize_environment(self, environment):
        from django.conf import settings
        environment.pop(MARKER, None)
        if (not getattr(settings, 'DESKTOP_STANDALONE', False) or settings.HOSTED
                or settings.DESKTOP_BOUNDARY or settings.LOCAL_ADMIN_ACCESS
                or self.district != settings.DISTRICT['id'] or not _direct(environment, self.origin)):
            return False
        environment[MARKER] = (_ISSUER, self.district, self.origin)
        return True


def _native_request(request):
    from django.conf import settings
    marker = request.META.get(MARKER)
    return (isinstance(marker, tuple) and len(marker) == 3 and marker[0] is _ISSUER
            and marker[1] == settings.DISTRICT['id'] and _direct(request.META, marker[2]))


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
