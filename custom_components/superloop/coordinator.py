import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import SuperloopClient

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
        self.daily_usage = None  # Store daily usage separately

    async def _async_update_data(self):
        """Fetch the latest service data from Superloop (regular usage)."""
        _LOGGER.debug("Coordinator update starting")
        try:
            services_data = await self.client.async_get_services()
            bb = services_data.get("broadband") or []
            _LOGGER.debug("Coordinator update successful: %s broadband services found", len(bb))
            return services_data
        except ConfigEntryAuthFailed as err:
            _LOGGER.error("Authentication failed during coordinator update: %s", err)
            # Re-raise so HA triggers reauth flow
            raise
        except Exception as err:
            _LOGGER.exception("Error fetching Superloop service data: %s", err)
            raise UpdateFailed(f"Error fetching Superloop service data: {err}") from err

    async def async_update_daily_usage(self):
        """Fetch daily broadband usage (you call this on your own schedule)."""
        try:
            # Ensure we have fresh services data
            if not self.data:
                await self.async_request_refresh()

            bb_list = (self.data or {}).get("broadband") or []
            if not bb_list:
                _LOGGER.warning("No broadband services returned; skipping daily usage fetch.")
                return

            # Prefer an ACTIVE service if present, otherwise fall back to first
            service = next((s for s in bb_list if (s.get("status") or "").upper() == "ACTIVE"), bb_list[0])
            service_id = service.get("id")
            if not service_id:
                _LOGGER.warning("No broadband service ID found; skipping daily usage fetch.")
                return

            _LOGGER.debug("Fetching Superloop daily usage for service_id=%s", service_id)
            self.daily_usage = await self.client.async_get_daily_usage(service_id)

        except ConfigEntryAuthFailed as err:
            _LOGGER.error("Authentication failed during daily usage fetch: %s", err)
            # Let HA handle reauth
            raise
        except Exception as err:
            # Don't raise UpdateFailed here unless you want to fail the whole coordinator cycle.
            # We log and keep last known daily_usage.
            _LOGGER.error("Failed to fetch daily usage: %s", err)
