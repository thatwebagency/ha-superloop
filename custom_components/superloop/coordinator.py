import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SuperloopClient

_LOGGER = logging.getLogger(__name__)

class SuperloopCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching Superloop service data."""

    def __init__(self, hass, client: SuperloopClient, update_interval_minutes: int = 15):
        """Initialize the Superloop Coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Superloop Coordinator",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.client = client

    async def _async_update_data(self):
        """Fetch data from Superloop API."""
        _LOGGER.debug("Fetching latest Superloop service data...")

        try:
            data = await self.client.async_get_services()
            _LOGGER.debug("Successfully fetched Superloop service data: %s", data)
            return data

        except Exception as err:
            _LOGGER.error("Failed to update Superloop data: %s", err)
            raise UpdateFailed(f"Error fetching Superloop data: {err}") from err
