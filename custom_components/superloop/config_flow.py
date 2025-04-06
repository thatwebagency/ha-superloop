"""Config flow for Superloop integration."""
import logging
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.data_entry_flow import FlowResult

from .api import SuperloopClient, SuperloopApiError
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    AUTH_ERROR_INVALID_CREDENTIALS
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

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
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
                _LOGGER.exception("Unexpected error during Superloop authentication")
                errors["base"] = "unknown"

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        """Handle reauth when tokens are no longer valid."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SuperloopOptionsFlowHandler(config_entry)


class SuperloopOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Superloop options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({})
        )