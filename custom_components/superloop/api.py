"""API client for Superloop."""
import logging
import aiohttp
import async_timeout
from typing import Any, Dict, Optional

from .const import API_BASE_URL, API_LOGIN_ENDPOINT, API_GET_SERVICES_ENDPOINT

_LOGGER = logging.getLogger(__name__)

class SuperloopApiError(Exception):
    """Exception to indicate an error from the Superloop API."""
    pass

class SuperloopClient:
    """API client for interacting with the Superloop API."""

    def __init__(self, email: str, password: str, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._email = email
        self._password = password
        self._session = session
        self._auth_token = None
        self._customer_id = None

    async def authenticate(self) -> bool:
        """Authenticate with the Superloop API and get an auth token."""
        try:
            with async_timeout.timeout(10):
                response = await self._session.post(
                    f"{API_BASE_URL}{API_LOGIN_ENDPOINT}",
                    json={"email": self._email, "password": self._password},
                )
                
                if response.status != 200:
                    _LOGGER.error("Authentication failed: %s", await response.text())
                    return False
                
                data = await response.json()
                self._auth_token = data.get("token")
                self._customer_id = data.get("customerId")
                
                if not self._auth_token or not self._customer_id:
                    _LOGGER.error("Authentication response missing token or customer ID")
                    return False
                
                return True
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            _LOGGER.error("Error authenticating with Superloop API: %s", error)
            return False

    async def get_services(self) -> Dict[str, Any]:
        """Get the services and usage data for the account."""
        if not self._auth_token or not self._customer_id:
            if not await self.authenticate():
                raise SuperloopApiError("Failed to authenticate with Superloop API")
        
        try:
            with async_timeout.timeout(10):
                headers = {"Authorization": f"Bearer {self._auth_token}"}
                response = await self._session.get(
                    f"{API_BASE_URL}{API_GET_SERVICES_ENDPOINT}/{self._customer_id}",
                    headers=headers,
                )
                
                if response.status == 401:
                    # Token might be expired, try to re-authenticate
                    if await self.authenticate():
                        # Retry with new token
                        headers = {"Authorization": f"Bearer {self._auth_token}"}
                        response = await self._session.get(
                            f"{API_BASE_URL}{API_GET_SERVICES_ENDPOINT}/{self._customer_id}",
                            headers=headers,
                        )
                    else:
                        raise SuperloopApiError("Failed to re-authenticate with Superloop API")
                
                if response.status != 200:
                    _LOGGER.error("Error fetching services: %s", await response.text())
                    raise SuperloopApiError(f"Failed to get services: {response.status}")
                
                return await response.json()
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            _LOGGER.error("Error fetching services from Superloop API: %s", error)
            raise SuperloopApiError(f"Error communicating with Superloop API: {error}")