import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import SuperloopClient

_LOGGER = logging.getLogger(__name__)

class SuperloopCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching Superloop service, speed-boost, and daily usage data."""

    def __init__(self, hass, client: SuperloopClient, update_interval_minutes: int = 15):
        super().__init__(
            hass,
            _LOGGER,
            name="Superloop Coordinator",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.client = client
        self.daily_usage = None
        self.speed_boost_status = None
        self.speed_boost_history = None  # optional; filled if we fetch it

    def _pick_service(self, services_data: dict) -> dict | None:
        """Pick the broadband service to operate on (prefer ACTIVE)."""
        bb_list = (services_data or {}).get("broadband") or []
        if not bb_list:
            return None
        return next((s for s in bb_list if (s.get("status") or "").upper() == "ACTIVE"), bb_list[0])

    async def _async_update_data(self):
        """Fetch the latest service + speed boost status from Superloop."""
        _LOGGER.debug("Coordinator update starting")
        try:
            services_data = await self.client.async_get_services()
            service = self._pick_service(services_data)

            if service and service.get("id"):
                service_id = service["id"]

                # --- Speed Boost status (primary flag the UI needs) ---
                try:
                    self.speed_boost_status = await self.client.async_get_speed_boost_status(service_id)
                    _LOGGER.debug("Speed boost status: %s", self.speed_boost_status)
                except ConfigEntryAuthFailed:
                    # Bubble up to trigger reauth
                    raise
                except Exception as e:
                    _LOGGER.warning("Speed boost status fetch failed: %s", e)

                # --- (Optional) Speed Boost history ---
                # Uncomment if you want history cached each cycle
                # try:
                #     self.speed_boost_history = await self.client.async_get_speed_boost_history(service_id)
                #     _LOGGER.debug("Speed boost history entries: %s", len(self.speed_boost_history or []))
                # except ConfigEntryAuthFailed:
                #     raise
                # except Exception as e:
                #     _LOGGER.info("Speed boost history fetch failed (non-fatal): %s", e)

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
            if not self.data:
                await self.async_request_refresh()

            service = self._pick_service(self.data or {})
            if not service or not service.get("id"):
                _LOGGER.warning("No broadband service ID found; skipping daily usage fetch.")
                return

            service_id = service["id"]
            _LOGGER.debug("Fetching Superloop daily usage for service_id=%s", service_id)
            self.daily_usage = await self.client.async_get_daily_usage(service_id)

        except ConfigEntryAuthFailed as err:
            _LOGGER.error("Authentication failed during daily usage fetch: %s", err)
            # Let HA handle reauth
            raise
        except Exception as err:
            # Log and keep last known daily_usage (don’t fail whole coordinator)
            _LOGGER.error("Failed to fetch daily usage: %s", err)
