"""The Superloop integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import SuperloopClient, SuperloopApiError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Superloop component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Superloop from a config entry."""
    session = async_get_clientsession(hass)
    
    # Get stored tokens
    access_token = entry.data.get(CONF_ACCESS_TOKEN)
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)
    
    client = SuperloopClient(
        session=session,
        access_token=access_token,
        refresh_token=refresh_token
    )
    
    coordinator = SuperloopDataUpdateCoordinator(
        hass,
        client=client,
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up all platforms for this device/entry
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Remove config entry from domain data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload the config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class SuperloopDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Superloop data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SuperloopClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self):
        """Update data from Superloop."""
        try:
            return await self.client.get_services()
        except SuperloopApiError as error:
            if "401" in str(error) or "Unauthorized" in str(error):
                try:
                    # Try to refresh the token
                    if await self.client.refresh_token():
                        # Retry with refreshed token
                        return await self.client.get_services()
                    else:
                        raise ConfigEntryAuthFailed("Failed to refresh access token")
                except Exception as refresh_error:
                    raise ConfigEntryAuthFailed(f"Authentication error: {refresh_error}")
            raise UpdateFailed(f"Error communicating with API: {error}")