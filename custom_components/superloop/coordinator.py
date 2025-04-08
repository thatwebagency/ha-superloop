import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
        try:
            return await self.client.async_get_services()
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
