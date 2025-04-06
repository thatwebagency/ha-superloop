"""Config flow for Superloop integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN, CONF_REFRESH_TOKEN
from .api import SuperloopClient, SuperloopApiError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    _LOGGER.debug("Starting validation of Superloop credentials")
    session = async_get_clientsession(hass)
    
    client = SuperloopClient(
        username=data[CONF_EMAIL],
        password=data[CONF_PASSWORD],
        session=session
    )

    try:
        if not await client.authenticate():
            _LOGGER.error("Authentication failed with provided credentials")
            raise InvalidAuth

        # Return info that you want to store in the config entry.
        _LOGGER.debug("Authentication successful")
        return {
            "title": f"Superloop ({data[CONF_EMAIL]})",
            CONF_TOKEN: client.get_access_token(),
            CONF_REFRESH_TOKEN: client.get_refresh_token()
        }
    except SuperloopApiError as error:
        _LOGGER.exception(f"API error during validation: {error}")
        raise CannotConnect from error
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception during validation: {e}")
        raise CannotConnect from e


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Superloop."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                return self.async_create_entry(
                    title=info["title"], 
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_TOKEN: info[CONF_TOKEN],
                        CONF_REFRESH_TOKEN: info[CONF_REFRESH_TOKEN]
                    }
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        """Handle reauthorization."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                entry = await self.async_set_unique_id(self.unique_id)
                self.hass.config_entries.async_update_entry(
                    entry, 
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_TOKEN: info[CONF_TOKEN],
                        CONF_REFRESH_TOKEN: info[CONF_REFRESH_TOKEN]
                    }
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""