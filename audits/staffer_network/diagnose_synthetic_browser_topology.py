"""Bounded local-only tab/window test; never opens a production browser profile."""
from __future__ import annotations

import asyncio
import contextlib
import json
import subprocess
import sys
import tempfile
import time

from playwright.async_api import async_playwright

from politico_profile_crawl_playwright import SNAPSHOT_SCRIPT


HTML = """<!doctype html><html><body><main>
<h1 class="profile-header__name">Synthetic Person</h1>
<div class="profile-header__desc">Synthetic Role, Synthetic Office</div>
<h2>Employment History</h2>
<div class="profile-employment-history__item">
<span class="profile-employment-history__employer">Synthetic Office</span>
<span class="profile-employment-history__title">Synthetic Role</span>
<span class="profile-employment-history__date">2024 - Present</span></div>
<h2>Education</h2><div class="profile-education__item">
<span class="profile-education__institution">Synthetic University</span>
<span class="profile-education__degree">Synthetic Degree</span></div>
</main></body></html>"""


async def topology(playwright, kind):
    with tempfile.TemporaryDirectory(prefix="melange-synthetic-topology-", ignore_cleanup_errors=True) as profile:
        context = await playwright.chromium.launch_persistent_context(
            profile, channel="chrome", headless=True,
            viewport={"width": 1440, "height": 1000},
            args=["--blink-settings=imagesEnabled=false"], timeout=10000,
        )
        try:
            print(json.dumps({"event": "LAUNCHED", "topology": kind}), flush=True)
            # Local HTML only. Abort any accidental page-origin network request.
            await context.route("**/*", lambda route: route.abort())
            pages = [context.pages[0]]
            await pages[0].set_content(HTML, wait_until="load", timeout=5000)
            if kind == "tabs":
                pages.append(await context.new_page())
            else:
                session = await context.new_cdp_session(pages[0])
                async with context.expect_page(timeout=5000) as opened:
                    await session.send("Target.createTarget", {
                        "url": "about:blank", "newWindow": True,
                    })
                pages.append(await opened.value)
                await session.detach()

            print(json.dumps({"event": "PAGES_CREATED", "topology": kind}), flush=True)
            await pages[1].set_content(HTML, wait_until="load", timeout=5000)

            windows = []
            for page in pages:
                session = await context.new_cdp_session(page)
                target = (await session.send("Target.getTargetInfo"))["targetInfo"]
                window = await session.send("Browser.getWindowForTarget", {
                    "targetId": target["targetId"],
                })
                windows.append(window["windowId"])
                await session.detach()

            print(json.dumps({"event": "FIXTURES_READY", "topology": kind, "distinct_windows": len(set(windows))}), flush=True)

            async def worker(index, page):
                result = {"worker": index, "trivial_ms": [], "snapshot_ms": [], "errors": []}
                for sample in range(8):
                    for label, expression in (("trivial", "() => 1"), ("snapshot", SNAPSHOT_SCRIPT)):
                        began = time.perf_counter()
                        try:
                            value = await asyncio.wait_for(page.evaluate(expression), 2)
                            result[label + "_ms"].append(round((time.perf_counter() - began) * 1000, 2))
                            if label == "snapshot":
                                assert value["profile_names"] == ["Synthetic Person"]
                                assert len(value["employment_history"]) == 1
                        except Exception as error:
                            result["errors"].append({"sample": sample, "phase": label, "error": type(error).__name__})
                            return result
                    await asyncio.sleep(0.025)
                return result

            results = await asyncio.gather(*(worker(i, page) for i, page in enumerate(pages)))
            result = {"topology": kind, "distinct_windows": len(set(windows)), "workers": results}
            print(json.dumps(result), flush=True)
            return result
        except Exception as error:
            print(json.dumps({"topology": kind, "setup_error": type(error).__name__, "message": str(error)[:300]}), flush=True)
            raise
        finally:
            for page in list(context.pages):
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(page.close(), 2)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(context.close(), 5)


async def run():
    async with async_playwright() as playwright:
        await topology(playwright, sys.argv[2])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--inner":
        asyncio.run(asyncio.wait_for(run(), 20))
    else:
        # Independent wall-clock watchdog also bounds hung Playwright shutdown.
        selected = sys.argv[1:] or ["windows", "tabs"]
        for kind in selected:
            if kind not in {"windows", "tabs"}:
                raise SystemExit("Expected windows or tabs")
            child = subprocess.Popen([sys.executable, "-u", __file__, "--inner", kind],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                output, _ = child.communicate(timeout=25)
            except subprocess.TimeoutExpired as expired:
                subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                               capture_output=True, timeout=3)
                output = expired.output or ""
                if isinstance(output, bytes):
                    output = output.decode("utf-8", errors="replace")
                print(json.dumps({"event": "OWNED_PROBE_WATCHDOG_TERMINATED", "topology": kind}), flush=True)
            print(output, end="", flush=True)
