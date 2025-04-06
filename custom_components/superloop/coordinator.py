"""DataUpdateCoordinator for the Superloop integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import aiohttp

from .api import SuperloopClient, SuperloopApiError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class SuperloopDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Superloop data."""

    def __init__(
        self, hass: HomeAssistant, client: SuperloopClient
    ) -> None:
        """Initialize the data update coordinator."""
        self.client = client
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        try:
            with async_timeout.timeout(10):
                return await self.client.get_services()
        except SuperloopApiError as error:
            raise UpdateFailed(f"Error communicating with API: {error}")