"""TiVo remote entity."""

from __future__ import annotations

import asyncio
import logging
from enum import StrEnum
from typing import Any

from const import TiVoConfig
from device import TiVoDevice
from ucapi import EntityTypes, StatusCodes, remote
from ucapi.remote import Features
from ucapi.remote import States as RemoteStates
from ucapi.ui import (
    Buttons,
    DeviceButtonMapping,
    Size,
    UiPage,
    create_btn_mapping,
    create_ui_icon,
    create_ui_text,
)
from ucapi_framework import create_entity_id
from ucapi_framework.entities import RemoteEntity
from ucapi_framework.helpers import RemoteAttributes

_LOG = logging.getLogger(__name__)


class TiVoCommand(StrEnum):
    """TiVo remote commands."""

    TIVO = "IRCODE TIVO"
    LIVETV = "IRCODE LIVETV"
    GUIDE = "IRCODE GUIDE"
    INFO = "IRCODE INFO"
    EXIT = "IRCODE EXIT"

    UP = "IRCODE UP"
    DOWN = "IRCODE DOWN"
    LEFT = "IRCODE LEFT"
    RIGHT = "IRCODE RIGHT"
    SELECT = "IRCODE SELECT"

    PLAY = "IRCODE PLAY"
    PAUSE = "IRCODE PAUSE"
    STOP = "KEYBOARD STOP"
    FORWARD = "IRCODE FORWARD"
    REVERSE = "IRCODE REVERSE"
    REPLAY = "IRCODE REPLAY"
    ADVANCE = "IRCODE ADVANCE"
    SLOW = "IRCODE SLOW"
    RECORD = "IRCODE RECORD"

    CHANNELUP = "IRCODE CHANNELUP"
    CHANNELDOWN = "IRCODE CHANNELDOWN"
    VOLUMEUP = "IRCODE VOLUMEUP"
    VOLUMEDOWN = "IRCODE VOLUMEDOWN"
    MUTE = "IRCODE MUTE"
    TVINPUT = "IRCODE TVINPUT"

    THUMBSUP = "IRCODE THUMBSUP"
    THUMBSDOWN = "IRCODE THUMBSDOWN"
    OPTIONS = "IRCODE OPTIONS"

    NUM0 = "IRCODE NUM0"
    NUM1 = "IRCODE NUM1"
    NUM2 = "IRCODE NUM2"
    NUM3 = "IRCODE NUM3"
    NUM4 = "IRCODE NUM4"
    NUM5 = "IRCODE NUM5"
    NUM6 = "IRCODE NUM6"
    NUM7 = "IRCODE NUM7"
    NUM8 = "IRCODE NUM8"
    NUM9 = "IRCODE NUM9"
    ENTER = "IRCODE ENTER"
    CLEAR = "IRCODE CLEAR"

    ACTION_A = "IRCODE ACTION_A"
    ACTION_B = "IRCODE ACTION_B"
    ACTION_C = "IRCODE ACTION_C"
    ACTION_D = "IRCODE ACTION_D"

    TELEPORT_TIVO = "TELEPORT TIVO"
    TELEPORT_LIVETV = "TELEPORT LIVETV"
    TELEPORT_GUIDE = "TELEPORT GUIDE"
    TELEPORT_NOWPLAYING = "TELEPORT NOWPLAYING"


SIMPLE_COMMANDS = [command.name for command in TiVoCommand]


class TiVoRemote(RemoteEntity):
    """Remote entity for TiVo button commands."""

    _device: TiVoDevice

    def __init__(self, config_device: TiVoConfig, device_instance: TiVoDevice) -> None:
        """Initialize the TiVo remote entity."""
        self._device = device_instance
        self._device_id = config_device.identifier

        entity_id = create_entity_id(EntityTypes.REMOTE, config_device.identifier)
        features = [Features.SEND_CMD]

        _LOG.debug("Initializing TiVo remote entity: %s", entity_id)

        super().__init__(
            entity_id,
            f"{config_device.name} Remote",
            features,
            attributes={
                remote.Attributes.STATE: RemoteStates.UNKNOWN,
            },
            simple_commands=SIMPLE_COMMANDS,
            button_mapping=self.create_button_mappings(),
            ui_pages=self.create_ui(),
            cmd_handler=self.handle_command,
        )

        self.subscribe_to_device(device_instance)

    async def sync_state(self) -> None:
        """Sync remote state from the device."""
        self.update(
            RemoteAttributes(
                STATE=RemoteStates.ON
                if self._device.is_connected
                else RemoteStates.UNAVAILABLE
            )
        )

    def create_button_mappings(self) -> list[DeviceButtonMapping | dict[str, Any]]:
        """Create hard-button mappings for the UC remote."""
        mappings = [
            create_btn_mapping(Buttons.DPAD_UP, TiVoCommand.UP.name),
            create_btn_mapping(Buttons.DPAD_DOWN, TiVoCommand.DOWN.name),
            create_btn_mapping(Buttons.DPAD_LEFT, TiVoCommand.LEFT.name),
            create_btn_mapping(Buttons.DPAD_RIGHT, TiVoCommand.RIGHT.name),
            create_btn_mapping(Buttons.DPAD_MIDDLE, TiVoCommand.SELECT.name),
        ]

        optional_mappings = {
            "BACK": TiVoCommand.LEFT.name,
            "HOME": TiVoCommand.TIVO.name,
            "MENU": TiVoCommand.TIVO.name,
            "INFO": TiVoCommand.INFO.name,
            "GUIDE": TiVoCommand.GUIDE.name,
            "CHANNEL_UP": TiVoCommand.CHANNELUP.name,
            "CHANNEL_DOWN": TiVoCommand.CHANNELDOWN.name,
            "VOLUME_UP": TiVoCommand.VOLUMEUP.name,
            "VOLUME_DOWN": TiVoCommand.VOLUMEDOWN.name,
            "MUTE": TiVoCommand.MUTE.name,
            "PLAY": TiVoCommand.PLAY.name,
            "PAUSE": TiVoCommand.PAUSE.name,
            "STOP": TiVoCommand.STOP.name,
            "PREV": TiVoCommand.REPLAY.name,
            "NEXT": TiVoCommand.ADVANCE.name,
            "REW": TiVoCommand.REVERSE.name,
            "FF": TiVoCommand.FORWARD.name,
            "RECORD": TiVoCommand.RECORD.name,
        }

        for button_name, command in optional_mappings.items():
            button = getattr(Buttons, button_name, None)

            if button is None:
                _LOG.debug("UC button enum not available: %s", button_name)
                continue

            mappings.append(create_btn_mapping(button, command))

        return mappings

    def create_ui(self) -> list[UiPage | dict[str, Any]]:
        """Create the TiVo remote UI pages."""
        return [
            self._create_navigation_page(),
            self._create_playback_page(),
            self._create_keypad_page(),
            self._create_shortcuts_page(),
        ]

    @staticmethod
    def _create_navigation_page() -> UiPage:
        """Create the navigation UI page."""
        page = UiPage("page1", "Navigation", grid=Size(6, 6))

        page.add(create_ui_text("TiVo", 0, 0, Size(2, 1), TiVoCommand.TIVO.name))
        page.add(create_ui_icon("uc:up-arrow", 2, 0, Size(2, 1), TiVoCommand.UP.name))
        page.add(create_ui_text("Guide", 4, 0, Size(2, 1), TiVoCommand.GUIDE.name))

        page.add(
            create_ui_icon("uc:left-arrow", 0, 1, Size(2, 1), TiVoCommand.LEFT.name)
        )
        page.add(create_ui_icon("uc:circle", 2, 1, Size(2, 1), TiVoCommand.SELECT.name))
        page.add(
            create_ui_icon("uc:right-arrow", 4, 1, Size(2, 1), TiVoCommand.RIGHT.name)
        )

        page.add(create_ui_text("Exit", 0, 2, Size(2, 1), TiVoCommand.EXIT.name))
        page.add(
            create_ui_icon("uc:down-arrow", 2, 2, Size(2, 1), TiVoCommand.DOWN.name)
        )
        page.add(create_ui_text("Info", 4, 2, Size(2, 1), TiVoCommand.INFO.name))

        page.add(create_ui_text("Live TV", 0, 3, Size(3, 1), TiVoCommand.LIVETV.name))
        page.add(
            create_ui_text(
                "Now Playing",
                3,
                3,
                Size(3, 1),
                TiVoCommand.TELEPORT_NOWPLAYING.name,
            )
        )

        page.add(create_ui_text("Ch +", 0, 4, Size(3, 1), TiVoCommand.CHANNELUP.name))
        page.add(create_ui_text("Ch -", 3, 4, Size(3, 1), TiVoCommand.CHANNELDOWN.name))

        page.add(create_ui_text("Vol +", 0, 5, Size(2, 1), TiVoCommand.VOLUMEUP.name))
        page.add(create_ui_text("Mute", 2, 5, Size(2, 1), TiVoCommand.MUTE.name))
        page.add(create_ui_text("Vol -", 4, 5, Size(2, 1), TiVoCommand.VOLUMEDOWN.name))

        return page

    @staticmethod
    def _create_playback_page() -> UiPage:
        """Create the playback UI page."""
        page = UiPage("page2", "Playback", grid=Size(6, 5))

        page.add(create_ui_text("Replay", 0, 0, Size(2, 1), TiVoCommand.REPLAY.name))
        page.add(create_ui_text("Play", 2, 0, Size(2, 1), TiVoCommand.PLAY.name))
        page.add(create_ui_text("Advance", 4, 0, Size(2, 1), TiVoCommand.ADVANCE.name))

        page.add(create_ui_text("Reverse", 0, 1, Size(2, 1), TiVoCommand.REVERSE.name))
        page.add(create_ui_text("Pause", 2, 1, Size(2, 1), TiVoCommand.PAUSE.name))
        page.add(create_ui_text("Forward", 4, 1, Size(2, 1), TiVoCommand.FORWARD.name))

        page.add(create_ui_text("Slow", 0, 2, Size(2, 1), TiVoCommand.SLOW.name))
        page.add(create_ui_text("Stop", 2, 2, Size(2, 1), TiVoCommand.STOP.name))
        page.add(create_ui_text("Record", 4, 2, Size(2, 1), TiVoCommand.RECORD.name))

        page.add(
            create_ui_text("Thumbs +", 0, 3, Size(3, 1), TiVoCommand.THUMBSUP.name)
        )
        page.add(
            create_ui_text("Thumbs -", 3, 3, Size(3, 1), TiVoCommand.THUMBSDOWN.name)
        )

        page.add(create_ui_text("Options", 0, 4, Size(3, 1), TiVoCommand.OPTIONS.name))
        page.add(create_ui_text("TV Input", 3, 4, Size(3, 1), TiVoCommand.TVINPUT.name))

        return page

    @staticmethod
    def _create_keypad_page() -> UiPage:
        """Create the numeric keypad UI page."""
        page = UiPage("page3", "Keypad", grid=Size(3, 5))

        page.add(create_ui_text("1", 0, 0, Size(1, 1), TiVoCommand.NUM1.name))
        page.add(create_ui_text("2", 1, 0, Size(1, 1), TiVoCommand.NUM2.name))
        page.add(create_ui_text("3", 2, 0, Size(1, 1), TiVoCommand.NUM3.name))

        page.add(create_ui_text("4", 0, 1, Size(1, 1), TiVoCommand.NUM4.name))
        page.add(create_ui_text("5", 1, 1, Size(1, 1), TiVoCommand.NUM5.name))
        page.add(create_ui_text("6", 2, 1, Size(1, 1), TiVoCommand.NUM6.name))

        page.add(create_ui_text("7", 0, 2, Size(1, 1), TiVoCommand.NUM7.name))
        page.add(create_ui_text("8", 1, 2, Size(1, 1), TiVoCommand.NUM8.name))
        page.add(create_ui_text("9", 2, 2, Size(1, 1), TiVoCommand.NUM9.name))

        page.add(create_ui_text("Clear", 0, 3, Size(1, 1), TiVoCommand.CLEAR.name))
        page.add(create_ui_text("0", 1, 3, Size(1, 1), TiVoCommand.NUM0.name))
        page.add(create_ui_text("Enter", 2, 3, Size(1, 1), TiVoCommand.ENTER.name))

        page.add(create_ui_text("Live TV", 0, 4, Size(3, 1), TiVoCommand.LIVETV.name))

        return page

    @staticmethod
    def _create_shortcuts_page() -> UiPage:
        """Create shortcut and teleport UI page."""
        page = UiPage("page4", "Shortcuts", grid=Size(4, 4))

        page.add(
            create_ui_text("TiVo", 0, 0, Size(2, 1), TiVoCommand.TELEPORT_TIVO.name)
        )
        page.add(
            create_ui_text(
                "Live TV",
                2,
                0,
                Size(2, 1),
                TiVoCommand.TELEPORT_LIVETV.name,
            )
        )

        page.add(
            create_ui_text(
                "Guide",
                0,
                1,
                Size(2, 1),
                TiVoCommand.TELEPORT_GUIDE.name,
            )
        )
        page.add(
            create_ui_text(
                "Now Playing",
                2,
                1,
                Size(2, 1),
                TiVoCommand.TELEPORT_NOWPLAYING.name,
            )
        )

        page.add(create_ui_text("A", 0, 2, Size(1, 1), TiVoCommand.ACTION_A.name))
        page.add(create_ui_text("B", 1, 2, Size(1, 1), TiVoCommand.ACTION_B.name))
        page.add(create_ui_text("C", 2, 2, Size(1, 1), TiVoCommand.ACTION_C.name))
        page.add(create_ui_text("D", 3, 2, Size(1, 1), TiVoCommand.ACTION_D.name))

        page.add(create_ui_text("Options", 0, 3, Size(2, 1), TiVoCommand.OPTIONS.name))
        page.add(create_ui_text("Exit", 2, 3, Size(2, 1), TiVoCommand.EXIT.name))

        return page

    async def handle_command(
        self,
        _entity: RemoteEntity,
        cmd_id: str,
        params: dict[str, Any] | None,
        _: Any | None = None,
    ) -> StatusCodes:
        """Handle remote commands."""
        del _entity, _

        _LOG.info("Received TiVo remote command: %s params=%s", cmd_id, params)

        try:
            match cmd_id:
                case remote.Commands.SEND_CMD | "send_cmd":
                    command = self._get_send_command(params)
                    await self._send_tivo_command(command)

                case remote.Commands.SEND_CMD_SEQUENCE | "send_cmd_sequence":
                    await self._send_sequence(params)

                case _:
                    await self._send_tivo_command(str(cmd_id))

            return StatusCodes.OK

        except (OSError, RuntimeError, ValueError, TimeoutError) as ex:
            _LOG.error("Error executing TiVo remote command %s: %s", cmd_id, ex)
            return StatusCodes.BAD_REQUEST

    async def _send_sequence(self, params: dict[str, Any] | None) -> None:
        """Handle remote send_cmd_sequence."""
        if not params:
            raise ValueError("Missing send_cmd_sequence parameters")

        sequence = params.get("sequence")
        delay = int(params.get("delay", 100))

        if not isinstance(sequence, list):
            raise ValueError("Missing or invalid command sequence")

        for command in sequence:
            await self._send_tivo_command(str(command))

            if delay > 0:
                await asyncio.sleep(delay / 1000)

    async def _send_tivo_command(self, command: str) -> None:
        """Map and send a TiVo command."""
        command = command.strip()

        if command.startswith("remote."):
            command = command.split(".", maxsplit=1)[1]

        mapped_command = self._map_command(command)
        await self._device.send_command(mapped_command)

    @staticmethod
    def _map_command(command: str) -> str:
        """Map a UI command to a TiVo device command."""
        command = command.strip()

        if not command:
            raise ValueError("Command cannot be empty")

        command_upper = command.upper()

        if command_upper in TiVoCommand.__members__:
            return TiVoCommand[command_upper].value

        if command_upper.startswith(("IRCODE ", "KEYBOARD ", "TELEPORT ")):
            return command_upper

        if command_upper.startswith(("SETCH ", "FORCECH ")):
            return command_upper

        return f"IRCODE {command_upper}"

    @staticmethod
    def _get_send_command(params: dict[str, Any] | None) -> str:
        """Extract send_cmd command parameter."""
        if not params:
            raise ValueError("Missing send_cmd parameters")

        command = params.get("command")

        if not command:
            raise ValueError("Missing send_cmd command")

        return str(command)
