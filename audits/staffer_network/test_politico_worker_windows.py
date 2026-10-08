import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from audits.staffer_network.politico_worker_windows import new_worker_window, window_id


class ExpectedPage:
    def __init__(self, page):
        self.value = asyncio.get_running_loop().create_future()
        self.value.set_result(page)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class WorkerWindowsTests(unittest.IsolatedAsyncioTestCase):
    def setup_context(self):
        session = SimpleNamespace(send=AsyncMock(), detach=AsyncMock())
        context = SimpleNamespace(new_cdp_session=AsyncMock(return_value=session))
        anchor = SimpleNamespace(context=context)
        page = SimpleNamespace(context=context)
        context.expect_page = Mock(return_value=ExpectedPage(page))
        return context, anchor, page, session

    async def test_created_page(self):
        context, anchor, page, session = self.setup_context()
        self.assertIs(await new_worker_window(context, anchor), page)
        session.send.assert_awaited_once_with("Target.createTarget", {"url": "about:blank", "newWindow": True})
        session.detach.assert_awaited_once()

    async def test_detach_on_failure(self):
        context, anchor, _, session = self.setup_context()
        session.send.side_effect = RuntimeError("synthetic failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            await new_worker_window(context, anchor)
        session.detach.assert_awaited_once()

    async def test_wrong_context_rejected(self):
        context, anchor, page, session = self.setup_context()
        page.context = object()
        with self.assertRaisesRegex(RuntimeError, "expected context"):
            await new_worker_window(context, anchor)
        session.detach.assert_awaited_once()

    async def test_window_id(self):
        context, _, page, session = self.setup_context()
        session.send.side_effect = [{"targetInfo": {"targetId": "synthetic-target"}}, {"windowId": 91}]
        self.assertEqual(await window_id(context, page), 91)
        session.send.assert_any_await("Browser.getWindowForTarget", {"targetId": "synthetic-target"})
        session.detach.assert_awaited_once()

    async def test_window_id_detaches_on_failure(self):
        context, _, page, session = self.setup_context()
        session.send.side_effect = RuntimeError("synthetic failure")
        with self.assertRaises(RuntimeError):
            await window_id(context, page)
        session.detach.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
