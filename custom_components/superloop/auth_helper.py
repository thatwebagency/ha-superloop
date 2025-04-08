"""Authentication helper for Superloop integration."""
import logging
import aiohttp
from urllib.parse import urlencode

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    AUTH_CALLBACK_PATH,
    AUTH_CALLBACK_NAME,
)

_LOGGER = logging.getLogger(__name__)

def register_auth_callback(hass: HomeAssistant, flow_id: str) -> bool:
    """Register the Superloop auth callback view."""
    
    # Check if the callback is already registered
    if hass.data.get(f"{DOMAIN}_{AUTH_CALLBACK_NAME}"):
        return True
    
    hass.data[f"{DOMAIN}_{AUTH_CALLBACK_NAME}"] = True
    
    # Create auth callback view
    auth_callback_view = SuperloopAuthCallbackView(hass, flow_id)
    hass.http.register_view(auth_callback_view)
    
    return True

class SuperloopAuthCallbackView(HomeAssistantView):
    """Superloop Authorization Callback View."""
    
    requires_auth = False
    url = AUTH_CALLBACK_PATH
    name = f"api:{DOMAIN}:auth-callback"
    
    def __init__(self, hass: HomeAssistant, flow_id: str):
        """Initialize the OAuth callback view."""
        self.hass = hass
        self.flow_id = flow_id
    
    async def get(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Handle OAuth callback from Superloop."""
        
        # Extract token from request
        token = request.query.get("token")
        
        if token:
            _LOGGER.debug("Got auth token from callback")
            
            # Forward the token to the config flow
            await self.hass.config_entries.flow.async_configure(
                flow_id=self.flow_id,
                user_input={"token": token}
            )
            
            # Return success response
            return aiohttp.web.Response(
                status=200,
                text="Authentication successful! You can close this window and return to Home Assistant."
            )
        
        _LOGGER.error("No auth token received in callback")
        return aiohttp.web.Response(
            status=400,
            text="No authentication token found. Please try again."
        )