"""TiVo mDNS discovery."""

import logging
import socket

from ucapi_framework.discovery import DiscoveredDevice, MDNSDiscovery
from zeroconf import ServiceInfo

_LOG = logging.getLogger(__name__)


class TiVoDiscovery(MDNSDiscovery):
    """Discover TiVo devices using mDNS."""

    def __init__(self) -> None:
        """Initialize TiVo mDNS discovery."""
        super().__init__(
            service_type="_tivo-remote._tcp.local.",
            timeout=5,
        )

    async def discover(self) -> list[DiscoveredDevice]:
        """Discover TiVo devices."""
        _LOG.info("Searching for TiVo devices via mDNS...")
        devices = await super().discover()
        _LOG.info("TiVo discovery complete, devices found: %d", len(devices))
        return devices

    def parse_mdns_service(
        self,
        service_info: ServiceInfo,
    ) -> DiscoveredDevice | None:
        """Parse mDNS service info."""
        _LOG.debug("Parsing TiVo mDNS service: %s", service_info.name)

        if not service_info.addresses:
            _LOG.debug("Ignoring TiVo service with no addresses: %s", service_info.name)
            return None

        address = self._get_ipv4_address(service_info)
        if not address:
            _LOG.debug(
                "Ignoring TiVo service with no IPv4 address: %s", service_info.name
            )
            return None

        properties = {
            key.decode() if isinstance(key, bytes) else str(key): (
                value.decode() if isinstance(value, bytes) else str(value)
            )
            for key, value in service_info.properties.items()
        }

        name = service_info.name.replace(f".{self.service_type}", "")
        identifier = properties.get("TSN", service_info.name)
        port = int(service_info.port or 0)

        _LOG.info("Found TiVo: %s @ %s:%d", name, address, port)

        return DiscoveredDevice(
            identifier=identifier,
            name=name,
            address=address,
            extra_data={
                **properties,
                "port": port,
            },
        )

    @staticmethod
    def _get_ipv4_address(service_info: ServiceInfo) -> str | None:
        """Return the first IPv4 address from a Zeroconf service."""
        for raw_address in service_info.addresses:
            try:
                return socket.inet_ntoa(raw_address)
            except OSError:
                continue

        return None
