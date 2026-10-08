"""Create distinct Chrome windows without creating another authenticated context."""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any


async def new_worker_window(context: Any, anchor: Any) -> Any:
    """Return one new about:blank window in the anchor's existing context."""
    if anchor.context is not context:
        raise ValueError("Anchor page belongs to a different context")
    session = await asyncio.wait_for(context.new_cdp_session(anchor), 5)
    try:
        async with context.expect_page(timeout=5000) as opened:
            await asyncio.wait_for(session.send("Target.createTarget", {
                "url": "about:blank", "newWindow": True,
            }), 5)
        page = await asyncio.wait_for(opened.value, 5)
        if page is anchor or page.context is not context:
            raise RuntimeError("New worker window does not belong to the expected context")
        return page
    finally:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(session.detach(), 2)


async def window_id(context: Any, page: Any) -> int:
    """Return Chromium's top-level window ID, not a tab/target ID."""
    if page.context is not context:
        raise ValueError("Page belongs to a different context")
    session = await asyncio.wait_for(context.new_cdp_session(page), 5)
    try:
        target = await asyncio.wait_for(session.send("Target.getTargetInfo"), 5)
        window = await asyncio.wait_for(session.send("Browser.getWindowForTarget", {
            "targetId": target["targetInfo"]["targetId"],
        }), 5)
        return int(window["windowId"])
    finally:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(session.detach(), 2)
