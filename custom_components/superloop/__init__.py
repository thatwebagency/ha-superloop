import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

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

    client = SuperloopClient(
        access_token=access_token,
        refresh_token=refresh_token,
        hass=hass,
        entry=entry,
    )

    coordinator = SuperloopCoordinator(hass, client, update_interval_minutes=15)

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
