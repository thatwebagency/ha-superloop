import logging
import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)

BASE_API_URL = "https://webservices.myexetel.exetel.com.au/api"
REFRESH_URL = "https://webservices.myexetel.exetel.com.au/api/auth/refresh"

class SuperloopApiError(Exception):
    """General Superloop API exception."""
    pass

class SuperloopClient:
    def __init__(self, access_token: str, refresh_token: str):
        """Initialize the Superloop API client."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._session = aiohttp.ClientSession()

    async def async_close(self):
        """Close the aiohttp session."""
        await self._session.close()

    async def async_get_services(self):
        """Fetch user services from Superloop."""
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Origin": "https://superhub.superloop.com",
            "Referer": "https://superhub.superloop.com",
        }

        try:
            async with async_timeout.timeout(10):
                response = await self._session.get(f"{BASE_API_URL}/getServices/", headers=headers)
                _LOGGER.debug("Superloop API getServices status: %s", response.status)
                data = await response.json()
                _LOGGER.debug("Superloop API getServices response: %s", data)

                if response.status == 401:
                    _LOGGER.warning("Access token expired, refreshing...")
                    await self.async_refresh_token()
                    return await self.async_get_services()

                if response.status != 200:
                    _LOGGER.error("Failed to fetch services: %s", response.status)
                    raise SuperloopApiError("Failed to fetch services")

                return data

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout fetching services")
            raise SuperloopApiError("Timeout fetching services") from ex


    async def async_refresh_token(self):
        """Refresh the access token using the refresh token."""
        payload = {"refresh_token": self._refresh_token}

        try:
            async with async_timeout.timeout(10):
                response = await self._session.post(REFRESH_URL, json=payload)

                if response.status != 200:
                    _LOGGER.error("Failed to refresh token")
                    raise SuperloopApiError("Failed to refresh token")

                data = await response.json()
                self._access_token = data["access_token"]
                self._refresh_token = data["refresh_token"]

                _LOGGER.info("Successfully refreshed token.")

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout refreshing token")
            raise SuperloopApiError("Timeout refreshing token") from ex

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token
