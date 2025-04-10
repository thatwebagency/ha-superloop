import logging
from datetime import timedelta, datetime

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SuperloopClient, SuperloopApiError

_LOGGER = logging.getLogger(__name__)

class SuperloopCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching Superloop service and daily usage data."""

    def __init__(self, hass, client: SuperloopClient, update_interval_minutes: int = 15):
        super().__init__(
            hass,
            _LOGGER,
            name="Superloop Coordinator",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.client = client
        self.daily_usage = None  # NEW: Store daily usage separately

    async def _async_update_data(self):
        """Fetch the latest service data from Superloop (regular usage)."""
        try:
            return await self.client.async_get_services()
        except Exception as err:
            raise UpdateFailed(f"Error fetching Superloop service data: {err}") from err

    async def async_update_daily_usage(self):
        """Fetch daily broadband usage once per day."""
        try:
            if not self.data:
                await self.async_request_refresh()

            service_id = self.data.get("broadband", [{}])[0].get("id")
            if not service_id:
                _LOGGER.warning("No broadband service ID found for daily usage fetch.")
                return

            now = datetime.now()
            month_str = now.strftime("%b")  # e.g., "Apr"
            year_str = now.strftime("%Y")   # e.g., "2025"

            _LOGGER.debug("Fetching Superloop daily usage for %s %s", month_str, year_str)
            self.daily_usage = await self.client.async_get_daily_usage(service_id, month_str, year_str)

        except Exception as err:
            _LOGGER.error("Failed to fetch daily usage: %s", err)
