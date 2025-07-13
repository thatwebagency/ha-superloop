import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from homeassistant.core import ServiceCall

from .api import SuperloopClient, SuperloopApiError
from .coordinator import SuperloopCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "superloop"
PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Superloop from a config entry."""
    _LOGGER.debug("Setting up Superloop entry: %s", entry.entry_id)

    access_token = entry.data["access_token"]
    refresh_token = entry.data["refresh_token"]
    expires_in = entry.data.get("expires_in")

    client = SuperloopClient(
        access_token=access_token,
        refresh_token=refresh_token,
        hass=hass,
        entry=entry,
        expires_in=expires_in,
    )

    coordinator = SuperloopCoordinator(hass, client, update_interval_minutes=30)

    try:
        await coordinator.async_config_entry_first_refresh()
        await coordinator.async_update_daily_usage()
    except ConfigEntryAuthFailed as err:
        _LOGGER.error("Authentication failed during setup: %s", err)
        raise ConfigEntryAuthFailed from err
    except SuperloopApiError as err:
        _LOGGER.error("Failed to connect to Superloop API: %s", err)
        raise ConfigEntryNotReady from err

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # === Scheduled Daily Usage Fetch ===
    async def _schedule_daily_usage(now):
        _LOGGER.debug("Scheduled daily usage fetch triggered")
        await coordinator.async_update_daily_usage()

    hass.async_create_task(coordinator.async_update_daily_usage())

    async_track_time_change(
        hass,
        _schedule_daily_usage,
        hour=6,
        minute=5,
        second=0,
    )

    # === Manual Refresh Data Service ===
    async def async_refresh_data_service(call: ServiceCall) -> None:
        """Handle refresh data service call."""
        _LOGGER.debug("Manual refresh data service called")
        coordinator = hass.data[DOMAIN].get(entry.entry_id)
        if coordinator:
            await coordinator.async_refresh()
            _LOGGER.info("Superloop data refreshed manually")

    # === Manual Refresh Token Service ===
    async def async_refresh_token_service(call: ServiceCall) -> None:
        """Handle manual token refresh."""
        _LOGGER.debug("Manual refresh token service called")
        coordinator = hass.data[DOMAIN].get(entry.entry_id)
        if not coordinator:
            _LOGGER.error("Coordinator not found for entry: %s", entry.entry_id)
            return
        try:
            await coordinator.client.async_check_and_refresh_token_if_needed(force=True)
            _LOGGER.info("Superloop token refreshed manually")
            # ✅ api.py already calls async_reload — no need to repeat it here
        except Exception as err:
            _LOGGER.exception("Failed to manually refresh token: %s", err)

    hass.services.async_register(DOMAIN, "refresh_data", async_refresh_data_service)
    hass.services.async_register(DOMAIN, "refresh_token", async_refresh_token_service)

    # === Silent Token Refresh Every 10 Minutes ===
    async def _background_refresh_tokens(now):
        _LOGGER.debug("Checking if token refresh is needed (background)...")
        coordinator = hass.data[DOMAIN].get(entry.entry_id)
        if coordinator:
            await coordinator.client.async_check_and_refresh_token_if_needed()

    async_track_time_interval(
        hass,
        _background_refresh_tokens,
        timedelta(minutes=10),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Superloop config entry."""
    _LOGGER.debug("Unloading Superloop entry: %s", entry.entry_id)

    coordinator: SuperloopCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.client.async_close()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok
