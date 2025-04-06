"""API client for Superloop."""
import logging
import asyncio
import aiohttp
import async_timeout
from typing import Any, Dict, Optional

from .const import (
    API_BASE_URL, 
    API_GET_SERVICES_ENDPOINT,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN
)

_LOGGER = logging.getLogger(__name__)

class SuperloopApiError(Exception):
    """Exception to indicate an error from the Superloop API."""
    pass

class SuperloopClient:
    """API client for interacting with the Superloop API."""

    def __init__(
        self, 
        session: aiohttp.ClientSession = None,
        access_token: str = None,
        refresh_token: str = None
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token

    def get_access_token(self) -> str:
        """Get the current access token."""
        return self._access_token
        
    def get_refresh_token(self) -> str:
        """Get the current refresh token."""
        return self._refresh_token

    async def get_services(self) -> Dict[str, Any]:
        """Get the services data from the Superloop API."""
        if not self._access_token:
            raise SuperloopApiError("No access token available")
        
        try:
            _LOGGER.debug("Fetching services from Superloop API")
            
            with async_timeout.timeout(30):
                headers = {"Authorization": f"Bearer {self._access_token}"}
                
                response = await self._session.get(
                    f"{API_BASE_URL}{API_GET_SERVICES_ENDPOINT}",
                    headers=headers
                )
                
                _LOGGER.debug(f"Get services response status: {response.status}")
                
                if response.status == 401:
                    # Token expired, try to refresh
                    _LOGGER.debug("Token expired, attempting to refresh")
                    if await self.refresh_token():
                        # Retry with new token
                        headers = {"Authorization": f"Bearer {self._access_token}"}
                        response = await self._session.get(
                            f"{API_BASE_URL}{API_GET_SERVICES_ENDPOINT}",
                            headers=headers
                        )
                        
                        if response.status != 200:
                            response_text = await response.text()
                            _LOGGER.error(f"Error fetching services after token refresh: {response.status}, {response_text}")
                            raise SuperloopApiError(f"Failed to get services after token refresh: {response.status}")
                    else:
                        raise SuperloopApiError("Failed to refresh token")
                
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error(f"Error fetching services: {response.status}, {response_text}")
                    raise SuperloopApiError(f"Failed to get services: {response.status}")
                
                data = await response.json()
                return data
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            _LOGGER.error(f"Error fetching services from Superloop API: {error}")
            raise SuperloopApiError(f"Error communicating with Superloop API: {error}")
        except Exception as e:
            _LOGGER.exception(f"Unexpected exception fetching services: {e}")
            raise SuperloopApiError(f"Unexpected error: {e}")
    
    async def refresh_token(self) -> bool:
        """Refresh the access token using refresh token."""
        # Implement token refresh logic here based on Superloop API
        # This is a placeholder - you'll need to adapt to Superloop's token refresh endpoint
        if not self._refresh_token:
            return False
            
        try:
            _LOGGER.debug("Refreshing access token")
            
            with async_timeout.timeout(30):
                refresh_data = {
                    "refresh_token": self._refresh_token
                }
                
                response = await self._session.post(
                    f"{API_BASE_URL}/v1/auth/refresh",  # Adjust to the actual refresh endpoint
                    json=refresh_data
                )
                
                if response.status != 200:
                    _LOGGER.error(f"Token refresh failed: {response.status}")
                    return False
                
                data = await response.json()
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token", self._refresh_token)
                
                return bool(self._access_token)
                
        except Exception as e:
            _LOGGER.exception(f"Error refreshing token: {e}")
            return False