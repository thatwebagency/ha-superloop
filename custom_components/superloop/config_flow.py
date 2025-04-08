"""Config flow for Superloop integration."""
import logging
import voluptuous as vol
import aiohttp
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.http import HomeAssistantView

from .api import SuperloopClient, SuperloopApiError
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    AUTH_ERROR_INVALID_CREDENTIALS,
    SUPERLOOP_LOGIN_URL,
    AUTH_CALLBACK_PATH
)

_LOGGER = logging.getLogger(__name__)


class SuperloopConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Superloop."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._username = None
        self._password = None
        self._client = None
        self._reauth_entry = None
        self._auth_token = None
        self._flow_id = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            if "use_browser_auth" in user_input and user_input["use_browser_auth"]:
                self._flow_id = self.flow_id
                return await self.async_step_browser_auth()
            
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            session = async_get_clientsession(self.hass)
            self._client = SuperloopClient(session=session)

            try:
                # Attempt to authenticate with provided credentials
                authenticated = await self._client.authenticate(self._username, self._password)
                
                if authenticated:
                    # Authentication successful, create entry
                    return self.async_create_entry(
                        title=self._username,
                        data={
                            CONF_USERNAME: self._username,
                            CONF_PASSWORD: self._password,
                            CONF_ACCESS_TOKEN: self._client.get_access_token(),
                            CONF_REFRESH_TOKEN: self._client.get_refresh_token()
                        }
                    )
                else:
                    errors["base"] = "invalid_auth"
            except SuperloopApiError as error:
                _LOGGER.exception("Error authenticating with Superloop API")
                errors["base"] = "invalid_auth" if str(error) == AUTH_ERROR_INVALID_CREDENTIALS else "cannot_connect"
            except Exception as error:
                _LOGGER.exception(f"Unexpected error during Superloop authentication: {error}")
                errors["base"] = "unknown"

        # Show form with browser auth option
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=self._username or ""): str,
                    vol.Required(CONF_PASSWORD, default=""): str,
                    vol.Optional("use_browser_auth", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={
                "browser_auth_description": "Use browser for authentication (recommended)"
            }
        )

    async def async_step_browser_auth(self, user_input=None):
        """Handle browser authentication step."""
        if user_input is not None and "token" in user_input:
            self._auth_token = user_input["token"]
            return await self.async_step_two_factor()

        # Register callback view
        callback_view = SuperloopAuthCallbackView(self)
        self.hass.http.register_view(callback_view)

        # Generate external URL for browser login
        return self.async_external_step(
            step_id="browser_auth",
            url=SUPERLOOP_LOGIN_URL
        )

    async def async_external_step_done(self, user_input=None):
        """Handle completion of external step."""
        if not self._auth_token:
            return self.async_abort(reason="no_auth_token")
        
        return await self.async_step_two_factor()

    async def async_step_two_factor(self, user_input=None):
        """Handle two-factor authentication step."""
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            self._client = SuperloopClient(session=session)
            
            try:
                # Set the auth token from the browser auth
                await self._client.set_browser_auth_token(self._auth_token)
                
                # Verify 2FA code
                verified = await self._client.verify_2fa(self._auth_token, user_input["verification_code"])
                
                if verified:
                    # 2FA successful, get the tokens and create entry
                    return self.async_create_entry(
                        title="Superloop Account",
                        data={
                            CONF_ACCESS_TOKEN: self._client.get_access_token(),
                            CONF_REFRESH_TOKEN: self._client.get_refresh_token()
                        }
                    )
                else:
                    errors["base"] = "invalid_verification_code"
            except SuperloopApiError as error:
                _LOGGER.exception(f"Error verifying 2FA code: {error}")
                errors["base"] = "verification_failed"
            except Exception as error:
                _LOGGER.exception(f"Unexpected error during 2FA verification: {error}")
                errors["base"] = "unknown"

        # Show form for 2FA code entry
        return self.async_show_form(
            step_id="two_factor",
            data_schema=vol.Schema(
                {
                    vol.Required("verification_code"): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "instruction": "Enter the verification code sent to your device."
            }
        )

    async def async_step_reauth(self, user_input=None):
        """Handle reauth when tokens are no longer valid."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_user()


class SuperloopOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Superloop options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({})
        )


class SuperloopAuthCallbackView(HomeAssistantView):
    """Superloop Authorization Callback View."""

    requires_auth = False
    url = AUTH_CALLBACK_PATH
    name = "api:superloop:auth-callback"

    def __init__(self, config_flow):
        """Initialize."""
        self.config_flow = config_flow

    async def get(self, request):
        """Handle callback from Superloop auth."""
        hass = request.app["hass"]
        
        # Extract token from request
        token = request.query.get("token")
        if token:
            await hass.config_entries.flow.async_configure(
                flow_id=self.config_flow.flow_id, user_input={"token": token}
            )
            return aiohttp.web.Response(
                status=200,
                text="Authentication successful! You can close this window and return to Home Assistant."
            )
        
        return aiohttp.web.Response(
            status=400,
            text="No authentication token found. Please try again."
        )