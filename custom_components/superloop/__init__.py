import logging
from datetime import time, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval

from .api import SuperloopClient, SuperloopApiError
from .coordinator import SuperloopCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "superloop"

# ✅ Platforms handled
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Superloop from a config entry."""
    _LOGGER.debug("Setting up Superloop entry: %s", entry.entry_id)

    access_token = entry.data["access_token"]
    refresh_token = entry.data["refresh_token"]
    expires_in = entry.data["expires_in"]

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
        await coordinator.async_update_daily_usage()  # 🆕 Daily usage fetch at startup
    except SuperloopApiError as err:
        _LOGGER.error("Failed to connect to Superloop API: %s", err)
        raise ConfigEntryNotReady from err

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # ✅ Forward to platforms (like sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ✅ DAILY FETCH SETUP
    async def _schedule_daily_usage(now):
        _LOGGER.debug("Scheduled daily usage fetch triggered")
        await coordinator.async_update_daily_usage()

    # Fetch daily usage once on boot
    hass.async_create_task(coordinator.async_update_daily_usage())

    # Schedule fetch at 6:05 AM every day
    async_track_time_change(
        hass,
        _schedule_daily_usage,
        hour=6,
        minute=5,
        second=0,
    )

    # ✅ BACKGROUND SILENT REFRESH SETUP
    async def _background_refresh_tokens(now):
        """Periodic background check to refresh token before expiry."""
        _LOGGER.debug("Checking if token refresh is needed...")
        await client.async_check_and_refresh_token_if_needed()

    # Every 10 minutes, check if we need to refresh token
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
