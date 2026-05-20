"""Constants and configuration models for the TiVo integration."""

from dataclasses import dataclass

DEFAULT_PORT = 31339


@dataclass
class TiVoConfig:
    """TiVo device configuration."""

    identifier: str
    name: str
    address: str
    port: int = DEFAULT_PORT
    platform: str = ""
