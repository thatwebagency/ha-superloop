import logging
from datetime import timedelta, datetime

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

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
        _LOGGER.debug("Coordinator update starting")
        try:
            services_data = await self.client.async_get_services()
            _LOGGER.debug("Coordinator update successful: %s broadband services found", 
                        len(services_data.get("broadband", [])))
            return services_data
        except ConfigEntryAuthFailed as err:
            _LOGGER.error("Authentication failed during coordinator update: %s", str(err))
            # CRITICAL: Re-raise authentication errors so HA can trigger reauth
            raise err
        except Exception as err:
            _LOGGER.exception("Error fetching Superloop service data: %s", str(err))
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

            _LOGGER.debug("Fetching Superloop daily usage for %s %s")
            self.daily_usage = await self.client.async_get_daily_usage(service_id)

        except Exception as err:
            _LOGGER.error("Failed to fetch daily usage: %s", err)
