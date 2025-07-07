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
            
            if mfa_method == "sms":
                self._mfa_method = "MfaOverSMS"
            elif mfa_method == "email":
                self._mfa_method = "MfaOverEmail"
            else:
                self._mfa_method = "MfaOverSMS"
                
            _LOGGER.debug("Attempting login for %s with MFA method: %s", self._email, self._mfa_method)
                
            try:
                _LOGGER.debug("Sending login request to %s", LOGIN_URL)
                self._access_token, self._refresh_token, self._expires_in = await self._attempt_login(self._email, self._password)
                _LOGGER.debug("Login successful, access token: %s..., refresh token: %s..., expires in: %s",
                             self._access_token[:10] if self._access_token else None,
                             self._refresh_token[:10] if self._refresh_token else None,
                             self._expires_in)
                
                _LOGGER.debug("Triggering MFA using method: %s", self._mfa_method)
                await self._trigger_mfa(self._access_token, self._mfa_method)
                _LOGGER.debug("MFA triggered successfully")
            except InvalidAuth:
                _LOGGER.error("Invalid auth credentials for %s", self._email)
                return self.async_show_form(
                    step_id="user",
                    errors={"base": "invalid_auth"},
                )
            except CannotConnect as ex:
                _LOGGER.error("Cannot connect to Superloop: %s", ex)
                return self.async_show_form(
                    step_id="user",
                    errors={"base": "cannot_connect"},
                )
            except Exception as ex:
                _LOGGER.exception("Unexpected error during login: %s", ex)
                return self.async_show_form(
                    step_id="user",
                    errors={"base": "unknown"},
                )

            _LOGGER.debug("Proceeding to 2FA step")
            return await self.async_step_2fa()

        _LOGGER.debug("Showing initial user form")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("email"): str,
                    vol.Required("password"): str,
                    vol.Required("mfa_method", default="sms"): vol.In(
                        {
                            "sms": "SMS (Text Message)",
                            "email": "Email",
                        }
                    ),
                }
            ),
        )

    async def async_step_2fa(self, user_input=None):
        _LOGGER.debug("In 2FA step")
        if user_input is not None:
            code = user_input["code"]
            _LOGGER.debug("2FA code entered: %s (length: %s)", "*" * len(code), len(code))

            try:
                # Get updated tokens after 2FA verification
                _LOGGER.debug("Verifying 2FA code with MFA method: %s", self._mfa_method)
                new_tokens = await self._verify_2fa_code(self._access_token, code, self._mfa_method)
                
                # Update tokens with the newly received ones after 2FA
                if new_tokens:
                    _LOGGER.debug("Received new tokens after 2FA: %s", {
                        k: (v if k not in ['token', 'access_token', 'refreshToken'] else f"{v[:10]}...{v[-10:]}" if v else None) 
                        for k, v in new_tokens.items()
                    })
                    
                    # Extract tokens - check for different possible key names
                    if "token" in new_tokens:
                        self._access_token = new_tokens["token"]
                    elif "access_token" in new_tokens:
                        self._access_token = new_tokens["access_token"]
                    elif "exchangeAccessToken" in new_tokens:
                        self._access_token = new_tokens["exchangeAccessToken"]
                        
                    if "refreshToken" in new_tokens:
                        self._refresh_token = new_tokens["refreshToken"]
                        
                    if "expiresIn" in new_tokens:
                        self._expires_in = new_tokens["expiresIn"]
                    
                    _LOGGER.debug("Updated tokens after 2FA verification: access=%s..., refresh=%s..., expires_in=%s", 
                                 self._access_token[:10] if self._access_token else None,
                                 self._refresh_token[:10] if self._refresh_token else None,
                                 self._expires_in)
                else:
                    _LOGGER.warning("2FA verification succeeded but no new tokens received")
                
            except InvalidAuth:
                _LOGGER.error("Invalid 2FA code entered")
                return self.async_show_form(
                    step_id="2fa",
                    errors={"base": "invalid_2fa"},
                )
            except Exception as ex:
                _LOGGER.exception("Unexpected error during 2FA verification: %s", str(ex))
                return self.async_show_form(
                    step_id="2fa",
                    errors={"base": "unknown"},
                )

            if self._reauth_entry:
                # Reauth flow
                _LOGGER.debug("Updating reauth entry with new post-2FA tokens")
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        "access_token": self._access_token,
                        "refresh_token": self._refresh_token,
                        "expires_in": self._expires_in,
                    },
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                _LOGGER.info("Reauth successful for %s", self._email)
                return self.async_abort(reason="reauth_successful")

            # Normal new flow
            _LOGGER.debug("Creating new config entry with post-2FA tokens")
            return self.async_create_entry(
                title=self._email,
                data={
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                    "expires_in": self._expires_in,
                },
            )

        _LOGGER.debug("Showing 2FA form")
        return self.async_show_form(
            step_id="2fa",
            data_schema=vol.Schema(
                {
                    vol.Required("code"): str,
                }
            ),
        )

    async def async_step_reauth(self, entry_data):
        """Handle a reauthentication flow."""
        _LOGGER.debug("Starting Superloop reauthentication flow")
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._email = self._reauth_entry.title  # preload email if possible
        _LOGGER.debug("Reauth for entry %s with email %s", self._reauth_entry.entry_id, self._email)

        return await self.async_step_user()

    async def _attempt_login(self, email: str, password: str):
        """Send login request and return tokens."""
        payload = {
            "username": email,
            "password": password,
            "persistLogin": True,
            "brand": "superloop",
        }

        _LOGGER.debug("Sending login payload for %s to %s", email, LOGIN_URL)

        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    response = await session.post(LOGIN_URL, json=payload)
                    status = response.status
                    _LOGGER.debug("Login response status: %s", status)
                    
                    if status != 200:
                        response_text = await response.text()
                        _LOGGER.error("Login failed. Status: %s, Response: %s", status, response_text[:200])
                        raise InvalidAuth()

                    data = await response.json()
                    _LOGGER.debug("Login successful with response keys: %s", list(data.keys()))
                    return data["access_token"], data["refresh_token"], data.get("expires_in", 14400)  # default to 4h if missing
        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout during login request")
            raise CannotConnect() from ex
        except Exception as ex:
            _LOGGER.exception("Unexpected error during login: %s", str(ex))
            raise

    async def _trigger_mfa(self, access_token: str, mfa_action: str):
        """Trigger MFA after login."""
        headers = {"Authorization": f"Bearer {access_token}"}
        _LOGGER.debug("Triggering MFA with action: %s", mfa_action)

        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    # First check MFA status
                    _LOGGER.debug("Checking MFA status at %s", MFA_URL)
                    mfa_resp = await session.get(MFA_URL, headers=headers)
                    mfa_status = mfa_resp.status
                    _LOGGER.debug("MFA status check response: %s", mfa_status)
                    
                    if mfa_status != 200:
                        mfa_text = await mfa_resp.text()
                        _LOGGER.warning("MFA status check returned non-200: %s %s", mfa_status, mfa_text[:100])
                    
                    # Create MFA request
                    _LOGGER.debug("Creating MFA request at %s with action %s", CREATE_MFA_URL, mfa_action)
                    create_resp = await session.post(CREATE_MFA_URL, json={"action": mfa_action}, headers=headers)
                    create_status = create_resp.status
                    _LOGGER.debug("Create MFA response status: %s", create_status)
                    
                    if create_status != 200:
                        create_text = await create_resp.text()
                        _LOGGER.warning("Create MFA returned non-200: %s %s", create_status, create_text[:100])
                        
        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout during MFA triggering")
            raise CannotConnect() from ex
        except Exception as ex:
            _LOGGER.exception("Unexpected error during MFA triggering: %s", str(ex))
            raise

    async def _verify_2fa_code(self, access_token: str, code: str, mfa_action: str):
        """Verify the entered 2FA code and return updated tokens."""
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {"action": mfa_action, "token": code}
        
        _LOGGER.debug("Sending 2FA verification request to %s with action: %s", VERIFY_MFA_URL, mfa_action)

        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    _LOGGER.debug("Making 2FA verification POST request")
                    response = await session.post(VERIFY_MFA_URL, json=payload, headers=headers)
                    status = response.status
                    _LOGGER.debug("2FA verification response status: %s", status)
                    
                    if status != 200:
                        response_text = await response.text()
                        _LOGGER.error("2FA verification failed. Status: %s, Response: %s", status, response_text[:200])
                        raise InvalidAuth()
                    
                    # Parse and return the updated tokens
                    result = await response.json()
                    _LOGGER.debug("2FA verification successful, received response with keys: %s", list(result.keys()))
                    return result
        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout during 2FA verification request")
            raise CannotConnect() from ex
        except Exception as ex:
            _LOGGER.exception("Unexpected error during 2FA verification: %s", str(ex))
            raise

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""