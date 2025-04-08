import logging
import aiohttp
import async_timeout
import asyncio

from homeassistant.exceptions import ConfigEntryAuthFailed

_LOGGER = logging.getLogger(__name__)

BASE_API_URL = "https://webservices.myexetel.exetel.com.au/api"
REFRESH_URL = "https://webservices.myexetel.exetel.com.au/api/auth/refresh"

class SuperloopApiError(Exception):
    """General Superloop API exception."""
    pass

class SuperloopClient:
    def __init__(self, access_token: str, refresh_token: str, hass, entry):
        """Initialize the Superloop API client."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._hass = hass
        self._entry = entry
        self._session = aiohttp.ClientSession()

    async def async_close(self):
        """Close the aiohttp session."""
        await self._session.close()

    async def async_get_services(self):
        """Fetch user services from Superloop, handle token expiration."""
        headers = self._build_headers()

        try:
            async with async_timeout.timeout(10):
                response = await self._session.get(f"{BASE_API_URL}/getServices/", headers=headers)
                _LOGGER.debug("Superloop API getServices status: %s", response.status)

                if response.status == 401:
                    _LOGGER.warning("Access token expired, trying refresh token...")
                    if await self.async_refresh_token():
                        # Try original request again with new token
                        headers = self._build_headers()
                        response = await self._session.get(f"{BASE_API_URL}/getServices/", headers=headers)
                        if response.status == 401:
                            raise ConfigEntryAuthFailed("Superloop reauthentication failed after refresh")
                    else:
                        raise ConfigEntryAuthFailed("Superloop refresh token invalid")

                if response.status != 200:
                    _LOGGER.error("Failed to fetch services: %s", response.status)
                    raise SuperloopApiError("Failed to fetch services")

                data = await response.json()
                _LOGGER.debug("Superloop API getServices response: %s", data)
                return data

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout fetching services")
            raise SuperloopApiError("Timeout fetching services") from ex

    async def async_refresh_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        payload = {"refresh_token": self._refresh_token}

        try:
            async with async_timeout.timeout(10):
                response = await self._session.post(REFRESH_URL, json=payload)

                if response.status != 200:
                    _LOGGER.error("Failed to refresh token")
                    return False

                data = await response.json()
                self._access_token = data["access_token"]
                self._refresh_token = data["refresh_token"]
                _LOGGER.info("Successfully refreshed tokens")

                # Update Home Assistant config entry with new tokens
                self._hass.config_entries.async_update_entry(
                    self._entry,
                    data={
                        "access_token": self._access_token,
                        "refresh_token": self._refresh_token,
                    }
                )
                return True

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout refreshing token")
            return False

    def _build_headers(self):
        """Helper to build auth headers."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Origin": "https://superhub.superloop.com",
            "Referer": "https://superhub.superloop.com",
        }

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token
