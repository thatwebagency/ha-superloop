import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import SuperloopClient, SuperloopApiError
from .coordinator import SuperloopCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "superloop"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Superloop from a config entry."""
    _LOGGER.debug("Setting up Superloop entry: %s", entry.entry_id)

    access_token = entry.data["access_token"]
    refresh_token = entry.data["refresh_token"]

    client = SuperloopClient(access_token, refresh_token)
    coordinator = SuperloopCoordinator(hass, client, update_interval_minutes=15)

    try:
        await coordinator.async_config_entry_first_refresh()
    except SuperloopApiError as err:
        _LOGGER.error("Failed to connect to Superloop API: %s", err)
        raise ConfigEntryNotReady from err

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 🔥 Add this to forward setup to sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Superloop config entry."""
    _LOGGER.debug("Unloading Superloop entry: %s", entry.entry_id)

    coordinator: SuperloopCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.client.async_close()

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return True
