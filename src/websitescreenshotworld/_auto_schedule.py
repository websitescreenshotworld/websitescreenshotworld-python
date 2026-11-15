from __future__ import annotations

from . import _requests
from ._config import ClientConfig
from ._models import Account, TriggerResult, read_response
from ._transport import AsyncTransport, SyncTransport

__all__ = ["AsyncAutoSchedule", "AutoSchedule"]


class AutoSchedule:
    """The Auto Schedule API. Reached as ``client.auto_schedule``."""

    def __init__(self, config: ClientConfig, transport: SyncTransport) -> None:
        self._config = config
        self._transport = transport

    def trigger_now(self, web_page_id: str) -> TriggerResult:
        """Capture a scheduled web page now, outside its schedule.

        The result arrives by webhook. Safe to repeat: while a capture of the page is pending,
        the answer is ``already_pending`` and nothing is charged.

        Args:
            web_page_id: The web page's id from the dashboard; webhooks call it ``schedule_id``.
        """
        request = _requests.trigger_now(self._config, web_page_id)
        return read_response(self._transport.send(request), TriggerResult._from_wire)

    def account(self) -> Account:
        """Whose key this is: its name and prefix, its product and the member who created it.

        Costs no capture, so it is also a cheap way to check a key works.
        """
        request = _requests.auto_schedule_account(self._config)
        return read_response(self._transport.send(request), Account._from_wire)


class AsyncAutoSchedule:
    """The Auto Schedule API for asyncio. Reached as ``client.auto_schedule``."""

    def __init__(self, config: ClientConfig, transport: AsyncTransport) -> None:
        self._config = config
        self._transport = transport

    async def trigger_now(self, web_page_id: str) -> TriggerResult:
        """Capture a scheduled web page now. See :meth:`AutoSchedule.trigger_now`."""
        request = _requests.trigger_now(self._config, web_page_id)
        return read_response(await self._transport.send(request), TriggerResult._from_wire)

    async def account(self) -> Account:
        """Whose key this is. See :meth:`AutoSchedule.account`."""
        request = _requests.auto_schedule_account(self._config)
        return read_response(await self._transport.send(request), Account._from_wire)
