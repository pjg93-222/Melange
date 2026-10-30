"""Program-owned first-run page; selected data and user dashboards stay separate."""
from __future__ import annotations

from html import escape
from pathlib import Path
import secrets
import stat

WORKSPACE_PATH = '/__desktop/workspace'


def _regular(path):
    try:
        info = Path(path).lstat()
        return (stat.S_ISREG(info.st_mode) and not Path(path).is_symlink()
                and not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return False


def empty_dashboard(data_root):
    """Recognize only our exact small template, never inspect a real dashboard."""
    from melange_bootstrap import WELCOME
    path = Path(data_root) / 'Moneyball.html'
    try:
        if not _regular(path) or path.stat().st_size > 65536:
            return False
        with path.open('rb') as stream:
            raw = stream.read(65537)
        return raw.replace(b'\r\n', b'\n') == WELCOME.encode('utf-8')
    except OSError:
        return False


class DesktopWorkspace:
    def __init__(self, app_id, data_root, *, connections=None):
        if app_id not in ('melange', 'mentat'):
            raise ValueError('Unsupported desktop workspace')
        self.app_id = app_id
        self.data_root = Path(data_root)
        self.connections = dict(connections or {})

    def replaces_empty_root(self):
        return self.app_id == 'melange' and empty_dashboard(self.data_root)

    def page(self, server):
        """Report installed-reader availability without treating it as full app data."""
        app = getattr(server, 'app', None) if self.app_id == 'mentat' else server
        reader = getattr(app, 'public_data', None)
        available = False
        try:
            catalogue = reader.catalogue() if reader is not None else None
            if self.app_id == 'mentat':
                available = (isinstance(catalogue, dict) and catalogue.get('available') is True
                             and catalogue.get('kind') == 'mentat.public-fec-tables.v1')
            else:
                available = (isinstance(catalogue, dict) and catalogue.get('status') == 'available'
                             and isinstance(catalogue.get('coverage'), dict)
                             and catalogue['coverage'].get('fullApplication') is False)
        except Exception:
            # A stale/changed input remains unavailable; no file paths or row data
            # are exposed by this setup page, and the reader keeps its own checks.
            pass
        name = 'Melange' if self.app_id == 'melange' else 'Mentat'
        public_title = 'Official payroll observations' if self.app_id == 'melange' else 'Public FEC tables'
        public_status = 'Ready to browse' if available else 'Not available yet'
        if self.app_id == 'melange':
            local = _regular(self.data_root / 'Moneyball.html') and not empty_dashboard(self.data_root)
            local_status = 'Local dashboard found' if local else 'Application workspace not connected'
            detail = 'Network, member, industry, and staffer analysis need their corresponding approved inputs.'
            existing_link = '<a href="/Moneyball.html">Open local dashboard</a>' if local else ''
        else:
            models = Path(self.connections.get('app_data', self.data_root / 'app-data'))
            local = all(_regular(models / filename) for filename in ('giving-models-current.json', 'pac-giving-current.json'))
            local_status = 'Local model selections found' if local else 'Application workspace not connected'
            detail = 'Forecasts and report analysis need current models, anchors, and report workbooks. Inputs are verified when opened.'
            existing_link = '<a href="/">Open Mentat console</a>'
        nonce = secrets.token_urlsafe(24)
        body = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} data workspace</title><style>
:root{{color-scheme:light dark;font:16px/1.6 system-ui,sans-serif}}body{{margin:0;background:#111820;color:#edf2f6}}
main{{max-width:780px;margin:7vh auto;padding:28px}}h1{{line-height:1.2}}section{{background:#1c2732;border:1px solid #40505f;border-radius:12px;padding:22px;margin:20px 0}}
h2{{font-size:1.2rem;margin-top:0}}a{{color:#9dd8ff}}button{{font:inherit;color:#10202b;background:#a8dbff;border:0;border-radius:6px;padding:9px 15px;cursor:pointer;margin:8px 12px 8px 0}}button:disabled{{opacity:.6;cursor:wait}}.note{{color:#b6c4d0}}#notice{{min-height:1.6em}}
</style></head><body><main><h1>{name} data workspace</h1>
<p>Your application updates and your analysis data are managed separately. Existing dashboards and saved work stay in their selected folders.</p>
<section><h2>{public_title}</h2><p id="public-status">{public_status}</p>
<p><a href="/public-data/">Browse public data</a></p><button id="refresh">Check public data</button>
<p class="note">These source tables cover part of the application. They do not replace the complete analysis workspace.</p></section>
<section><h2>Complete analysis workspace</h2><p>{escape(local_status)}</p><p>{escape(detail)}</p>
<button id="connect">Connect approved workspace</button> {existing_link}
<p class="note">Choose a folder you are authorized to access in Settings. Application data packages, when available, are downloaded separately.</p></section>
<p id="notice" role="status" aria-live="polite"></p>
<noscript>Use Settings in the application menu to connect an approved workspace.</noscript>
<script nonce="{nonce}">
'use strict';
const notice=document.getElementById('notice');
async function act(button,action,success){{button.disabled=true;notice.textContent='';try{{await action();notice.textContent=success;}}catch{{notice.textContent='This action could not finish. Use Settings or try again from the application menu.';}}finally{{button.disabled=false;}}}}
document.getElementById('connect').addEventListener('click',event=>act(event.currentTarget,()=>window.desktop.openWorkspaceSettings(),'Choose your approved workspace in Settings.'));
document.getElementById('refresh').addEventListener('click',event=>act(event.currentTarget,()=>window.desktop.refreshModuleData(),'Public data check requested. The application status shows its progress.'));
</script></main></body></html>'''
        policy = ("default-src 'none'; script-src 'nonce-" + nonce + "'; style-src 'unsafe-inline'; "
                  "base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        return body.encode('utf-8'), policy
