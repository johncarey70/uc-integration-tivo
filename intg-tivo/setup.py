"""
Setup flow for TiVo Unfolded Circle integration.
"""

import logging
from typing import Any

from ucapi import (
    IntegrationSetupError,
    RequestUserInput,
    SetupError,
    UserDataResponse,
)
from ucapi_framework.discovery import DiscoveredDevice
from ucapi_framework.setup import BaseSetupFlow

from const import DEFAULT_PORT, TiVoConfig

_LOG = logging.getLogger(__name__)


class TiVoSetupFlow(BaseSetupFlow[TiVoConfig]):
    """TiVo setup flow with mDNS discovery and manual fallback."""

    async def discover_devices(self) -> list[DiscoveredDevice]:
        """Run TiVo discovery."""
        _LOG.info("TiVoSetupFlow.discover_devices called")

        devices = await super().discover_devices()

        _LOG.info(
            "TiVoSetupFlow.discover_devices returned %d device(s)",
            len(devices),
        )
        return devices

    def get_manual_entry_form(self) -> RequestUserInput:
        """Return the manual TiVo device entry form."""
        _LOG.info("Showing TiVo manual setup form")

        return RequestUserInput(
            {"en": "TiVo Setup"},
            [
                {
                    "id": "name",
                    "label": {"en": "Name"},
                    "field": {"text": {"value": "TiVo"}},
                },
                {
                    "id": "address",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port"},
                    "field": {
                        "number": {
                            "value": DEFAULT_PORT,
                            "min": 1,
                            "max": 65535,
                        }
                    },
                },
                {
                    "id": "identifier",
                    "label": {"en": "TSN"},
                    "field": {"text": {"value": ""}},
                },
            ],
        )

    def format_discovered_device_label(self, device: DiscoveredDevice) -> str:
        """Format discovered TiVo devices in the setup dropdown."""
        tsn = self._get_extra_value(device, "TSN", device.identifier)

        return f"{device.name} - {tsn} ({device.address})"

    async def prepare_input_from_discovery(
        self,
        discovered: DiscoveredDevice,
        additional_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert discovered TiVo data into manual-entry-style input values."""
        _ = additional_input

        tsn = self._get_extra_value(discovered, "TSN", discovered.identifier)
        port = self._get_extra_value(discovered, "port", DEFAULT_PORT)
        platform = self._get_extra_value(discovered, "platform", "")

        _LOG.info(
            "Preparing TiVo config from discovery: name=%s tsn=%s address=%s port=%s",
            discovered.name,
            tsn,
            discovered.address,
            port,
        )

        return {
            "identifier": str(tsn).strip(),
            "name": str(discovered.name).strip(),
            "address": str(discovered.address).strip(),
            "port": self._parse_port(port),
            "platform": str(platform).strip(),
        }

    async def query_device(
        self,
        input_values: dict[str, Any],
    ) -> TiVoConfig | SetupError | RequestUserInput:
        """Validate setup input and return a TiVo device configuration."""
        _LOG.info("TiVoSetupFlow.query_device called: %s", input_values)

        name = str(input_values.get("name", "")).strip()
        address = str(input_values.get("address", "")).strip()
        identifier = str(input_values.get("identifier", "")).strip()
        port = self._parse_port(input_values.get("port", DEFAULT_PORT))
        platform = str(input_values.get("platform", "")).strip()

        if not address:
            _LOG.warning("TiVo setup failed: address is required")
            return SetupError(error_type=IntegrationSetupError.NOT_FOUND)

        if port < 1 or port > 65535:
            _LOG.warning("TiVo setup failed: invalid port %s", port)
            return SetupError(error_type=IntegrationSetupError.OTHER)

        if not name:
            name = address

        if not identifier:
            identifier = address

        _LOG.info(
            "Configured TiVo device: name=%s identifier=%s address=%s port=%s",
            name,
            identifier,
            address,
            port,
        )

        return TiVoConfig(
            identifier=identifier,
            name=name,
            address=address,
            port=port,
            platform=platform,
        )

    async def get_additional_configuration_screen(
        self,
        device_config: TiVoConfig,
        previous_input: dict[str, Any],
    ) -> RequestUserInput | None:
        """Ask the user to confirm or change the device name before saving."""
        _ = previous_input

        return RequestUserInput(
            {"en": "Confirm TiVo Name"},
            [
                {
                    "id": "info",
                    "label": {"en": "Device Found"},
                    "field": {
                        "label": {
                            "value": {
                                "en": (
                                    "Confirm the name shown on the remote, "
                                    "or change it before saving."
                                )
                            }
                        }
                    },
                },
                {
                    "id": "name",
                    "label": {"en": "Name"},
                    "field": {"text": {"value": device_config.name}},
                },
                {
                    "id": "address_info",
                    "label": {"en": "IP Address"},
                    "field": {
                        "label": {
                            "value": {
                                "en": f"{device_config.address}:{device_config.port}"
                            }
                        }
                    },
                },
                {
                    "id": "identifier",
                    "label": {"en": "TSN"},
                    "field": {"label": {"value": {"en": device_config.identifier}}},
                },
            ],
        )

    async def handle_additional_configuration_response(
        self,
        msg: UserDataResponse,
    ) -> TiVoConfig | SetupError | RequestUserInput | None:
        """Validate the confirmed name before the config is saved."""
        name = str(msg.input_values.get("name", "")).strip()

        if self._pending_device_config is None:
            _LOG.warning("TiVo setup failed: missing pending device config")
            return SetupError(error_type=IntegrationSetupError.OTHER)

        if not name:
            name = str(self._pending_device_config.address).strip() or "TiVo"

        self._pending_device_config.name = name
        return None

    @staticmethod
    def _get_extra_value(
        device: DiscoveredDevice,
        key: str,
        default: Any = "",
    ) -> Any:
        """Return a value from discovery extra_data."""
        extra_data = device.extra_data or {}
        value = extra_data.get(key, default)

        if isinstance(value, bytes):
            return value.decode(errors="ignore")

        return value

    @staticmethod
    def _parse_port(value: Any) -> int:
        """Parse a setup or discovery port value."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return DEFAULT_PORT
