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

class SuperloopConfigFlow(config_entries.ConfigFlow, domain="superloop"):
    """Handle a config flow for Superloop."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._email = user_input["email"]
            self._password = user_input["password"]

            try:
                # Step 1: Attempt login
                self._access_token, self._refresh_token = await self._attempt_login(self._email, self._password)
                # Step 2: Trigger SMS
                await self._trigger_mfa_sms(self._access_token)
            except InvalidAuth:
                return self.async_show_form(
                    step_id="user",
                    errors={"base": "invalid_auth"},
                )
            except CannotConnect:
                return self.async_show_form(
                    step_id="user",
                    errors={"base": "cannot_connect"},
                )

            return await self.async_step_2fa()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("email"): str,
                    vol.Required("password"): str,
                }
            ),
        )

    async def async_step_2fa(self, user_input=None):
        if user_input is not None:
            code = user_input["code"]

            try:
                await self._verify_2fa_code(self._access_token, code)
            except InvalidAuth:
                return self.async_show_form(
                    step_id="2fa",
                    errors={"base": "invalid_2fa"},
                )

            # Success! Save token
            return self.async_create_entry(
                title=self._email,
                data={
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                },
            )

        return self.async_show_form(
            step_id="2fa",
            data_schema=vol.Schema(
                {
                    vol.Required("code"): str,
                }
            ),
        )

    async def _attempt_login(self, email: str, password: str):
        """Send login request and return tokens."""
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
                    return data["access_token"], data["refresh_token"]
        except asyncio.TimeoutError as ex:
            raise CannotConnect() from ex

    async def _trigger_mfa_sms(self, access_token: str):
        """Trigger SMS MFA after login."""
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    await session.get(MFA_URL, headers=headers)
                    await session.post(CREATE_MFA_URL, json={"action": "MfaOverSMS"}, headers=headers)
        except asyncio.TimeoutError as ex:
            raise CannotConnect() from ex

    async def _verify_2fa_code(self, access_token: str, code: str):
        """Verify the entered 2FA code."""
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {"action": "MfaOverSMS", "token": code}

        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    response = await session.post(VERIFY_MFA_URL, json=payload, headers=headers)
                    if response.status != 200:
                        raise InvalidAuth()
        except asyncio.TimeoutError as ex:
            raise CannotConnect() from ex

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""
