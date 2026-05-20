"""
This module implements a Unfolded Circle integration driver for TiVo DVR devices.

:copyright: (c) 2025 by John Carey.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os

from ucapi_framework import (
    BaseConfigManager,
    BaseIntegrationDriver,
    get_config_path,
)

from const import TiVoConfig
from device import TiVoDevice
from discover import TiVoDiscovery
from remote import TiVoRemote
from setup import TiVoSetupFlow

_LOG = logging.getLogger("driver")


async def main():
    """Start the Remote Two integration driver."""
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)s:%(name)s:%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("device").setLevel(level)
    logging.getLogger("remote").setLevel(level)
    logging.getLogger("setup").setLevel(level)

    driver = BaseIntegrationDriver(
        device_class=TiVoDevice,
        entity_classes=[
            TiVoRemote,
        ],
    )
    driver.config_manager = BaseConfigManager(
        get_config_path(driver.api.config_dir_path),
        driver.on_device_added,
        driver.on_device_removed,
        config_class=TiVoConfig,
    )

    await driver.register_all_configured_devices()

    discovery = TiVoDiscovery()
    setup_handler = TiVoSetupFlow.create_handler(driver, discovery=discovery)
    await driver.api.init("driver.json", setup_handler)

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
