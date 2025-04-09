import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import SuperloopClient

_LOGGER = logging.getLogger(__name__)

class SuperloopCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching Superloop service data."""

    def __init__(self, hass, client: SuperloopClient, update_interval_minutes: int = 15):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Superloop Coordinator",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.client = client

    async def _async_update_data(self):
        """Fetch the latest service data from Superloop."""
        _LOGGER.debug("Fetching latest Superloop service data...")

        try:
            data = await self.client.async_get_services()
            _LOGGER.debug("Successfully fetched Superloop service data")
            return data

        except ConfigEntryAuthFailed:
            _LOGGER.error("Authentication error while updating Superloop data, need reauth")
            raise

        except Exception as err:
            _LOGGER.error("Failed to update Superloop data: %s", err)
            raise UpdateFailed(f"Error fetching Superloop data: {err}") from err
