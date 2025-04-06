"""The Superloop integration."""
import logging
import asyncio
import voluptuous as vol
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import Platform

from .api import SuperloopClient, SuperloopApiError
from .const import (
    DOMAIN,
    PLATFORMS,
    UPDATE_INTERVAL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN
)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Superloop component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Superloop from a config entry."""
    _LOGGER.debug("Setting up Superloop integration")
    
    session = async_get_clientsession(hass)
    
    # Get stored tokens from config entry
    access_token = entry.data.get(CONF_ACCESS_TOKEN)
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    
    client = SuperloopClient(session=session, access_token=access_token, refresh_token=refresh_token)
    
    # If we don't have tokens, try to authenticate
    if not access_token or not refresh_token:
        if not username or not password:
            raise ConfigEntryNotReady("Missing credentials and no tokens available")
        
        try:
            _LOGGER.debug("No tokens available, authenticating with username/password")
            authenticated = await client.authenticate(username, password)
            if not authenticated:
                raise ConfigEntryNotReady("Authentication failed")
        except SuperloopApiError as err:
            raise ConfigEntryNotReady(f"Error authenticating: {err}")
    
    # Create coordinator
    coordinator = SuperloopDataUpdateCoordinator(hass, client)
    
    # Fetch initial data to validate the connection
    await coordinator.async_config_entry_first_refresh()
    
    # Store client and coordinator in hass data
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    
    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Reload entry when options are updated
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload the config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

class SuperloopDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Superloop data."""
    
    def __init__(self, hass: HomeAssistant, client: SuperloopClient):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client
        
    async def _async_update_data(self):
        """Fetch data from Superloop API."""
        try:
            return await self.client.get_services()
        except SuperloopApiError as err:
            _LOGGER.error(f"Error fetching Superloop data: {err}")
            raise UpdateFailed(f"Error communicating with Superloop API: {err}")