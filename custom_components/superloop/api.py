"""API client for Superloop."""
import logging
import asyncio
import aiohttp
import async_timeout
from typing import Any, Dict, Optional, Tuple

from .const import (
    API_BASE_URL, 
    API_GET_SERVICES_ENDPOINT,
    API_AUTH_TOKEN_ENDPOINT,
    AUTH_BRAND,
    AUTH_PERSIST_LOGIN,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    AUTH_ERROR_INVALID_CREDENTIALS,
    AUTH_ERROR_GENERIC
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

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Superloop API using username and password."""
        try:
            _LOGGER.debug("Authenticating with Superloop API")
            
            auth_data = {
                "username": username,
                "password": password,
                "persistLogin": AUTH_PERSIST_LOGIN,
                "brand": AUTH_BRAND
            }
            
            with async_timeout.timeout(30):
                response = await self._session.post(
                    f"{API_BASE_URL}{API_AUTH_TOKEN_ENDPOINT}",
                    json=auth_data
                )
                
                _LOGGER.debug(f"Authentication response status: {response.status}")
                
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error(f"Authentication failed: {response.status}, {response_text}")
                    if response.status == 401:
                        raise SuperloopApiError(AUTH_ERROR_INVALID_CREDENTIALS)
                    else:
                        raise SuperloopApiError(f"{AUTH_ERROR_GENERIC}: {response.status}")
                
                data = await response.json()
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                
                return bool(self._access_token and self._refresh_token)
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            _LOGGER.error(f"Error during authentication: {error}")
            raise SuperloopApiError(f"Error communicating with Superloop API: {error}")
        except SuperloopApiError:
            raise
        except Exception as e:
            _LOGGER.exception(f"Unexpected exception during authentication: {e}")
            raise SuperloopApiError(f"Unexpected error: {e}")
    
    def get_access_token(self) -> str:
        """Get the current access token."""
        return self._access_token
        
    def get_refresh_token(self) -> str:
        """Get the current refresh token."""
        return self._refresh_token

    def set_tokens(self, access_token: str, refresh_token: str) -> None:
        """Set the access and refresh tokens."""
        self._access_token = access_token
        self._refresh_token = refresh_token

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
        if not self._refresh_token:
            _LOGGER.error("No refresh token available")
            return False
            
        try:
            _LOGGER.debug("Refreshing token")
            
            with async_timeout.timeout(30):
                refresh_data = {
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "persistLogin": AUTH_PERSIST_LOGIN,
                    "brand": AUTH_BRAND
                }
                
                response = await self._session.post(
                    f"{API_BASE_URL}{API_AUTH_TOKEN_ENDPOINT}", 
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