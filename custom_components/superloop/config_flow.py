"""Config flow for Superloop integration."""
import logging
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.data_entry_flow import FlowResult

from .api import SuperloopClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class SuperloopConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Superloop."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._api_client = None
        self._username = None
        self._password = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._username = user_input["email"]
            self._password = user_input["password"]

            session = async_get_clientsession(self.hass)
            self._api_client = SuperloopClient(
                username=self._username,
                password=self._password,
                session=session
            )

            success, result = await self._api_client.authenticate()

            if success:
                if result and result.get("requires_2fa"):
                    # User needs to enter 2FA code
                    return await self.async_step_2fa()
                
                # Authentication successful
                return self.async_create_entry(
                    title=self._username,
                    data={
                        "username": self._username,
                        "password": self._password,  # Consider using a token-based approach instead
                        "access_token": self._api_client.get_access_token(),
                        "refresh_token": self._api_client.get_refresh_token(),
                    },
                )
            
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("email"): str,
                vol.Required("password"): str,
            }),
            errors=errors,
        )

    async def async_step_2fa(self, user_input=None):
        """Handle the 2FA step."""
        errors = {}

        if user_input is not None:
            # Verify 2FA code
            success = await self._api_client.verify_2fa(user_input["code"])
            
            if success:
                # Authentication successful
                return self.async_create_entry(
                    title=self._username,
                    data={
                        "username": self._username,
                        "password": self._password,  # Consider using a token-based approach instead
                        "access_token": self._api_client.get_access_token(),
                        "refresh_token": self._api_client.get_refresh_token(),
                    },
                )
            
            errors["base"] = "invalid_code"

        return self.async_show_form(
            step_id="2fa",
            data_schema=vol.Schema({
                vol.Required("code"): str,
            }),
            errors=errors,
            description_placeholders={"message": "Please enter the verification code sent to your mobile"}
        )