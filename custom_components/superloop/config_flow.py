import asyncio
import logging
import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

DOMAIN = "superloop"

LOGIN_URL = "https://webservices.myexetel.exetel.com.au/api/auth/token"
MFA_URL = "https://webservices-api.superloop.com/v1/mfa"
CREATE_MFA_URL = "https://webservices-api.superloop.com/v1/create-mfa"
VERIFY_MFA_URL = "https://webservices-api.superloop.com/v1/verify-mfa"

class SuperloopConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Superloop."""

    VERSION = 1

    def __init__(self):
        self._reauth_entry = None
        self._email = None
        self._password = None
        self._access_token = None
        self._refresh_token = None
        self._expires_in = None
        self._mfa_method = "MfaOverSMS"

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Starting user setup step")
        if user_input is not None:
            self._email = user_input["email"]
            self._password = user_input["password"]
            mfa_method = user_input.get("mfa_method", "sms")

            self._mfa_method = {
                "sms": "MfaOverSMS",
                "email": "MfaOverEmail"
            }.get(mfa_method, "MfaOverSMS")

            _LOGGER.debug("Attempting login for %s with MFA method: %s", self._email, self._mfa_method)

            try:
                self._access_token, self._refresh_token, self._expires_in = await self._attempt_login(self._email, self._password)
                _LOGGER.debug("Login successful")
                await self._trigger_mfa(self._access_token, self._mfa_method)
            except InvalidAuth:
                return self.async_show_form(step_id="user", errors={"base": "invalid_auth"})
            except CannotConnect:
                return self.async_show_form(step_id="user", errors={"base": "cannot_connect"})
            except Exception as ex:
                _LOGGER.exception("Unexpected error during login: %s", ex)
                return self.async_show_form(step_id="user", errors={"base": "unknown"})

            return await self.async_step_2fa()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("email"): str,
                vol.Required("password"): str,
                vol.Required("mfa_method", default="sms"): vol.In({
                    "sms": "SMS (Text Message)",
                    "email": "Email",
                }),
            }),
        )

    async def async_step_2fa(self, user_input=None):
        if user_input is not None:
            code = user_input["code"]
            try:
                await self._verify_2fa_code(self._access_token, code, self._mfa_method)
            except InvalidAuth:
                return self.async_show_form(step_id="2fa", errors={"base": "invalid_2fa"})
            except Exception as ex:
                _LOGGER.exception("Unexpected error during 2FA verification: %s", str(ex))
                return self.async_show_form(step_id="2fa", errors={"base": "unknown"})

            if self._reauth_entry:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        "access_token": self._access_token,
                        "refresh_token": self._refresh_token,
                        "expires_in": self._expires_in,
                    },
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

            return self.async_create_entry(
                title=self._email,
                data={
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                    "expires_in": self._expires_in,
                },
            )

        return self.async_show_form(
            step_id="2fa",
            data_schema=vol.Schema({
                vol.Required("code"): str,
            }),
        )

    async def async_step_reauth(self, entry_data):
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._email = self._reauth_entry.title
        return await self.async_step_user()

    async def _attempt_login(self, email: str, password: str):
        payload = {
            "username": email,
            "password": password,
            "persistLogin": True,
            "brand": "superloop",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    response = await session.post(LOGIN_URL, json=payload)
                    if response.status != 200:
                        raise InvalidAuth()
                    data = await response.json()
                    return data["access_token"], data["refresh_token"], data.get("expires_in", 14400)
        except asyncio.TimeoutError:
            raise CannotConnect()
        except Exception as ex:
            _LOGGER.exception("Unexpected error during login: %s", str(ex))
            raise

    async def _trigger_mfa(self, access_token: str, mfa_action: str):
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    await session.get(MFA_URL, headers=headers)
                    await session.post(CREATE_MFA_URL, json={"action": mfa_action}, headers=headers)
        except asyncio.TimeoutError:
            raise CannotConnect()
        except Exception as ex:
            _LOGGER.exception("Unexpected error during MFA triggering: %s", str(ex))
            raise

    async def _verify_2fa_code(self, access_token: str, code: str, mfa_action: str):
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {"action": mfa_action, "token": code}
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    response = await session.post(VERIFY_MFA_URL, json=payload, headers=headers)
                    if response.status != 200:
                        raise InvalidAuth()
        except asyncio.TimeoutError:
            raise CannotConnect()
        except Exception as ex:
            _LOGGER.exception("Unexpected error during 2FA verification: %s", str(ex))
            raise

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""
