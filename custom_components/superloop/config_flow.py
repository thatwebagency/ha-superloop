"""Config flow for Superloop integration."""
import logging
import voluptuous as vol
from typing import Any, Dict, Optional
import secrets
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.data_entry_flow import FlowResult
from homeassistant.components.http import HomeAssistantView

from .api import SuperloopClient
from .const import (
    DOMAIN,
    AUTH_CALLBACK_PATH,
    AUTH_CALLBACK_NAME,
    SUPERLOOP_LOGIN_URL,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN
)

_LOGGER = logging.getLogger(__name__)

class SuperloopConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Superloop."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._state = None
        self._session = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # Generate a random state for security
        self._state = secrets.token_hex(16)
        self._session = async_get_clientsession(self.hass)
        
        # Register the callback view if not already registered
        self._register_auth_callback()
        
        return self.async_external_step(
            step_id="auth",
            url=f"{SUPERLOOP_LOGIN_URL}?state={self._state}&redirect_uri={self.hass.config.api.base_url}{AUTH_CALLBACK_PATH}"
        )

    async def async_step_auth(self, user_input=None):
        """Handle the callback after authorization."""
        # This will not be called directly, 
        # but will be the target of the external_step when the callback view redirects
        return self.async_external_step_done(next_step_id="finish")

    async def async_step_finish(self, data=None):
        """Handle the final step after OAuth."""
        if not data or not data.get(CONF_ACCESS_TOKEN):
            return self.async_abort(reason="auth_failed")
        
        # Create entry with the received tokens
        return self.async_create_entry(
            title="Superloop",
            data={
                CONF_ACCESS_TOKEN: data[CONF_ACCESS_TOKEN],
                CONF_REFRESH_TOKEN: data.get(CONF_REFRESH_TOKEN, "")
            }
        )

    def _register_auth_callback(self):
        """Register the auth callback handler."""
        if not hasattr(self.hass, AUTH_CALLBACK_NAME):
            self.hass.http.register_view(SuperloopAuthCallbackView())
            setattr(self.hass, AUTH_CALLBACK_NAME, True)


class SuperloopAuthCallbackView(HomeAssistantView):
    """Superloop Authorization Callback View."""

    url = AUTH_CALLBACK_PATH
    name = "api:superloop:auth"
    requires_auth = False

    @callback
    async def get(self, request):
        """Handle callback from Superloop."""
        hass = request.app["hass"]
        
        # Get URL parameters
        state = request.query.get("state")
        access_token = request.query.get("access_token")
        refresh_token = request.query.get("refresh_token")
        error = request.query.get("error")
        
        if error:
            _LOGGER.error(f"Error during authorization: {error}")
            return self.json({"error": error})
        
        # Find the flow based on the state
        for flow in hass.config_entries.flow.async_progress():
            if flow["handler"] == DOMAIN and flow.get("context", {}).get("state") == state:
                # Complete the flow with the tokens
                await hass.config_entries.flow.async_configure(
                    flow["flow_id"], 
                    {
                        CONF_ACCESS_TOKEN: access_token, 
                        CONF_REFRESH_TOKEN: refresh_token
                    }
                )
                
                # Show success page
                return self.json({"success": True})
        
        # No matching flow found
        _LOGGER.error("No matching authorization flow found")
        return self.json({"error": "invalid_state"})