"""The Superloop integration."""
from __future__ import annotations

import logging
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS, CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN, CONF_REFRESH_TOKEN
from .coordinator import SuperloopDataUpdateCoordinator
from .api import SuperloopClient

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Superloop component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Superloop from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    _LOGGER.debug(f"Setting up Superloop integration for {entry.data.get(CONF_EMAIL)}")
    
    # Use the Home Assistant session for better connection management
    session = async_get_clientsession(hass)
    
    # Create the API client
    client = SuperloopClient(
        username=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        session=session,
        access_token=entry.data.get(CONF_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN)
    )
    
    # Create the coordinator that will handle data updates
    coordinator = SuperloopDataUpdateCoordinator(hass, client)
    
    # Initial data fetch
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading Superloop integration for {entry.data.get(CONF_EMAIL)}")
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok