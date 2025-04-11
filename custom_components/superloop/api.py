import logging
import aiohttp
import async_timeout
import asyncio
from datetime import datetime, timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed

_LOGGER = logging.getLogger(__name__)

BASE_API_URL = "https://webservices.myexetel.exetel.com.au/api"
REFRESH_URL = "https://webservices.myexetel.exetel.com.au/api/auth/token/refresh"

class SuperloopApiError(Exception):
    """General Superloop API exception."""
    pass

class SuperloopClient:
    def __init__(self, access_token: str, refresh_token: str, hass, entry, expires_in: int = None):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._hass = hass
        self._entry = entry
        self._session = aiohttp.ClientSession()
        if expires_in:
            self._token_expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
        else:
            self._token_expiry_time = None

    async def async_close(self):
        """Close session."""
        if not self._session.closed:
            await self._session.close()

    def _build_headers(self):
        """Build auth headers."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Origin": "https://superhub.superloop.com",
            "Referer": "https://superhub.superloop.com",
        }

    async def async_get_services(self):
        """Fetch user services."""
        headers = self._build_headers()

        try:
            async with async_timeout.timeout(10):
                response = await self._session.get(f"{BASE_API_URL}/getServices/", headers=headers)
                _LOGGER.debug("Superloop API getServices status: %s", response.status)

                if response.status == 401:
                    _LOGGER.warning("Access token expired, trying to refresh...")
                    try:
                        await self._try_refresh_token()
                    except ConfigEntryAuthFailed as err:
                        _LOGGER.error("Failed to refresh token, raising auth failed.")
                        raise ConfigEntryAuthFailed("Token refresh failed") from err

                    headers = self._build_headers()
                    response = await self._session.get(f"{BASE_API_URL}/getServices/", headers=headers)
                    if response.status == 401:
                        raise ConfigEntryAuthFailed("Superloop reauthentication failed after refresh")

                if response.status != 200:
                    _LOGGER.error("Failed to fetch services: %s", response.status)
                    raise SuperloopApiError("Failed to fetch services")

                data = await response.json()
                _LOGGER.debug("Superloop API getServices response: %s", data)
                return data

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout fetching services")
            raise SuperloopApiError("Timeout fetching services") from ex

    async def async_get_daily_usage(self, service_id: int):
        """Fetch daily broadband usage."""
        headers = self._build_headers()
        url = f"{BASE_API_URL}/getBroadbandDailyUsage/{service_id}"

        try:
            _LOGGER.debug("Fetching daily usage - URL: %s", url)
            async with async_timeout.timeout(40):
                response = await self._session.get(url, headers=headers)

                if response.status == 401:
                    _LOGGER.warning("Token expired during daily usage fetch, refreshing...")
                    try:
                        await self._try_refresh_token()
                    except ConfigEntryAuthFailed as err:
                        _LOGGER.error("Failed to refresh token during daily usage")
                        raise ConfigEntryAuthFailed("Failed to refresh token during daily usage") from err

                    headers = self._build_headers()
                    response = await self._session.get(url, headers=headers)
                    if response.status == 401:
                        raise ConfigEntryAuthFailed("Superloop reauthentication failed after refresh")

                if response.status != 200:
                    _LOGGER.error("Failed to fetch daily usage: HTTP %s", response.status)
                    raise SuperloopApiError("Failed to fetch daily usage")

                data = await response.json()
                _LOGGER.debug("Daily usage response: %s", data)
                return data

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout fetching daily usage")
            raise SuperloopApiError("Timeout fetching daily usage") from ex

    async def _try_refresh_token(self):
        """Refresh access token."""
        payload = {"refresh_token": self._refresh_token}

        try:
            async with async_timeout.timeout(10):
                response = await self._session.post(REFRESH_URL, json=payload)

                if response.status != 200:
                    _LOGGER.error("Failed to refresh token (status %s)", response.status)
                    raise ConfigEntryAuthFailed("Superloop refresh token invalid")

                data = await response.json()
                self._access_token = data["access_token"]
                self._refresh_token = data["refresh_token"]
                expires_in = data.get("expires_in", 14400)  # default to 4h if missing
                self._token_expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

                _LOGGER.info("Successfully refreshed tokens")

                self._hass.config_entries.async_update_entry(
                    self._entry,
                    data={
                        "access_token": self._access_token,
                        "refresh_token": self._refresh_token,
                    }
                )

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout refreshing token")
            raise ConfigEntryAuthFailed("Timeout refreshing token") from ex

    async def async_check_and_refresh_token_if_needed(self):
        """Check if access token is close to expiry and refresh if needed."""
        now = datetime.utcnow()

        if self._token_expiry_time is None:
            _LOGGER.warning("Token expiry time not set, skipping silent refresh check.")
            return

        # If less than 10 minutes remaining, refresh proactively
        if (self._token_expiry_time - now) < timedelta(minutes=10):
            _LOGGER.info("Access token nearing expiry, refreshing proactively.")
            try:
                await self._try_refresh_token()
            except ConfigEntryAuthFailed:
                _LOGGER.error("Proactive token refresh failed, reauthentication needed soon.")

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token
