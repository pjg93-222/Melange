from pathlib import Path
from playwright.sync_api import sync_playwright


URL = ('http://127.0.0.1:8811/?a.source=snapshot&a.id=culac-20260921'
       '&a.committee=C00007880&a.cycle=2024#evidence')
OUTPUT = Path(__file__).resolve().parents[2] / 'outputs' / 'pac-fec-citations-20260921'


def capture(page, name):
    page.goto(URL, wait_until='domcontentloaded', timeout=120_000)
    page.locator('.evidence-pane').wait_for(timeout=120_000)
    page.locator('.pane-rows').click()
    activity = page.locator('details').filter(has_text='Selected PAC’s candidate activity as filed').first
    activity.locator(':scope > summary').click()
    row = activity.locator('tbody tr').filter(has_text='LAWLER, MICHAEL').first
    row.scroll_into_view_if_needed(timeout=120_000)
    row.locator('.filing-ledger > summary').click()
    page.wait_for_timeout(300)
    page.screenshot(path=OUTPUT / name)


OUTPUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as runtime:
    browser = runtime.chromium.launch(channel='msedge', headless=True)
    desktop = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    capture(desktop, 'pac-screen-citations-desktop.png')
    browser.close()
