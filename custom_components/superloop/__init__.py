"""The Superloop integration."""
import logging
import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SuperloopClient
from .const import DOMAIN, CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]  # Add other platforms as needed

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Superloop component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Superloop from a config entry."""
    # Get a session
    session = async_get_clientsession(hass)
    
    # Create API client
    client = SuperloopClient(
        session=session,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN)
    )
    
    try:
        # Test the connection by fetching services
        services = await client.get_services()
        
        # Store the client
        hass.data[DOMAIN][entry.entry_id] = client
        
        # Set up all platforms
        for platform in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )
        
        return True
        
    except Exception as e:
        _LOGGER.error(f"Failed to set up Superloop integration: {e}")
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Unload platforms
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    
    # Remove from hass data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok