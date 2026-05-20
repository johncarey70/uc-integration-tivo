"""TiVo device connection and TCP command handling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ucapi_framework.device import DeviceEvents, PersistentConnectionDevice

from const import DEFAULT_PORT, TiVoConfig

_LOG = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_COMMAND_TIMEOUT = 5.0

LIVETV_READY = "LIVETV_READY"
CH_FAILED = "CH_FAILED"
CH_STATUS = "CH_STATUS"


class TiVoCommandError(Exception):
    """Raised when a TiVo command fails."""


class TiVoDevice(PersistentConnectionDevice):
    """TiVo TCP remote-control device."""

    def __init__(self, device_config: TiVoConfig, *args: Any, **kwargs: Any) -> None:
        """Initialize the TiVo device."""
        super().__init__(device_config, *args, **kwargs)

        self._write_lock = asyncio.Lock()
        self._connected_event = asyncio.Event()
        self._last_response: str | None = None
        self._live_tv_ready_waiter: asyncio.Future[None] | None = None

    @property
    def config(self) -> TiVoConfig:
        """Return typed TiVo config."""
        return self._device_config

    @property
    def identifier(self) -> str:
        """Return device identifier."""
        return str(self.config.identifier)

    @property
    def name(self) -> str:
        """Return device name."""
        return str(self.config.name)

    @property
    def port(self) -> int:
        """Return TiVo TCP remote-control port."""
        return int(getattr(self.config, "port", DEFAULT_PORT) or DEFAULT_PORT)

    @property
    def platform(self) -> str:
        """Return TiVo advertised platform, if known."""
        return str(getattr(self.config, "platform", "") or "")

    @property
    def address(self) -> str:
        """Return device address."""
        return str(self.config.address)

    @property
    def log_id(self) -> str:
        """Return log identifier."""
        return f"{self.name} ({self.address}:{self.port})"

    @property
    def is_connected(self) -> bool:
        """Return True if the TiVo TCP connection is active."""
        return self._connection is not None and self._connected_event.is_set()

    @property
    def last_response(self) -> str | None:
        """Return the last response received from the TiVo."""
        return self._last_response

    async def establish_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the TiVo TCP connection."""
        _LOG.debug("[%s] Opening TiVo TCP connection", self.log_id)

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.address, self.port),
            timeout=DEFAULT_CONNECT_TIMEOUT,
        )

        _LOG.debug("[%s] TiVo TCP socket opened", self.log_id)
        return reader, writer

    async def close_connection(self) -> None:
        """Close the TiVo TCP connection."""
        self._connected_event.clear()

        if not self._connection:
            return

        _reader, writer = self._connection

        writer.close()
        await writer.wait_closed()

        _LOG.debug("[%s] TiVo TCP socket closed", self.log_id)

    async def maintain_connection(self) -> None:
        """Read TiVo responses until the connection closes."""
        if not self._connection:
            raise ConnectionError("TiVo connection missing")

        reader, _writer = self._connection
        self._connected_event.set()
        self.events.emit(DeviceEvents.UPDATE)

        _LOG.debug("[%s] TiVo response loop started", self.log_id)

        try:
            while not self._stop_reconnect.is_set():
                line = await reader.readline()

                if not line:
                    raise ConnectionError("TiVo connection closed")

                response = line.decode(errors="ignore").strip()

                if response:
                    self._handle_response(response)

        finally:
            self._connected_event.clear()
            _LOG.debug("[%s] TiVo response loop stopped", self.log_id)

    async def wait_connected(self, timeout: float = DEFAULT_COMMAND_TIMEOUT) -> None:
        """Wait until the TCP socket is connected."""
        if self.is_connected:
            return

        await asyncio.wait_for(self._connected_event.wait(), timeout=timeout)

    async def send_command(
        self,
        command: str,
        *,
        wait_connected: bool = True,
        timeout: float = DEFAULT_COMMAND_TIMEOUT,
    ) -> None:
        """Send a raw TiVo TCP command."""
        command = self._normalize_command(command)

        if wait_connected:
            await self.wait_connected(timeout=timeout)

        if not self._connection:
            raise ConnectionError("TiVo is not connected")

        async with self._write_lock:
            _reader, writer = self._connection

            _LOG.debug("[%s] -> %s", self.log_id, command)

            writer.write(f"{command}\r".encode("ascii"))
            await writer.drain()

    async def send_ircode(self, code: str) -> None:
        """Send an IRCODE button command."""
        code = self._normalize_token(code)
        await self.send_command(f"IRCODE {code}")

    async def send_keyboard(self, code: str) -> None:
        """Send a KEYBOARD command."""
        code = self._normalize_token(code)
        await self.send_command(f"KEYBOARD {code}")

    async def teleport(self, screen: str) -> None:
        """Teleport to a TiVo screen."""
        screen = self._normalize_token(screen)
        await self.send_command(f"TELEPORT {screen}")

    async def go_live_tv(self, timeout: float = DEFAULT_COMMAND_TIMEOUT) -> None:
        """Teleport to Live TV and wait for LIVETV_READY."""
        if self._live_tv_ready_waiter and not self._live_tv_ready_waiter.done():
            self._live_tv_ready_waiter.cancel()

        self._live_tv_ready_waiter = asyncio.get_running_loop().create_future()

        await self.send_command("TELEPORT LIVETV")

        try:
            await asyncio.wait_for(self._live_tv_ready_waiter, timeout=timeout)
        finally:
            self._live_tv_ready_waiter = None

    async def set_channel(
        self,
        channel: str | int,
        sub_channel: str | int | None = None,
        *,
        force: bool = False,
    ) -> None:
        """Tune the TiVo to a channel."""
        command = "FORCECH" if force else "SETCH"
        channel_value = self._normalize_channel(channel)

        if sub_channel is None or str(sub_channel).strip() == "":
            await self.send_command(f"{command} {channel_value}")
            return

        sub_channel_value = self._normalize_channel(sub_channel)
        await self.send_command(f"{command} {channel_value} {sub_channel_value}")

    async def force_channel(
        self,
        channel: str | int,
        sub_channel: str | int | None = None,
    ) -> None:
        """Force tune the TiVo to a channel."""
        await self.set_channel(channel, sub_channel, force=True)

    def _handle_response(self, response: str) -> None:
        """Handle one TiVo response line."""
        self._last_response = response

        _LOG.debug("[%s] <- %s", self.log_id, response)

        if response == LIVETV_READY:
            self._resolve_live_tv_ready()
            return

        if response.startswith(CH_STATUS):
            self.events.emit(DeviceEvents.UPDATE, self.identifier)
            return

        if response.startswith(CH_FAILED):
            _LOG.warning("[%s] Channel command failed: %s", self.log_id, response)
            return

        _LOG.debug("[%s] Unhandled TiVo response: %s", self.log_id, response)

    def _resolve_live_tv_ready(self) -> None:
        """Resolve the pending Live TV waiter."""
        if self._live_tv_ready_waiter and not self._live_tv_ready_waiter.done():
            self._live_tv_ready_waiter.set_result(None)

    @staticmethod
    def _normalize_command(command: str) -> str:
        """Normalize a raw TiVo command."""
        command = command.strip()

        if not command:
            raise TiVoCommandError("Command cannot be empty")

        return command.upper()

    @staticmethod
    def _normalize_token(value: str) -> str:
        """Normalize a TiVo command token."""
        value = value.strip().replace(" ", "_")

        if not value:
            raise TiVoCommandError("Command token cannot be empty")

        return value.upper()

    @staticmethod
    def _normalize_channel(value: str | int) -> str:
        """Normalize a channel value."""
        channel = str(value).strip()

        if not channel.isdigit():
            raise TiVoCommandError(f"Invalid channel: {value}")

        return channel
