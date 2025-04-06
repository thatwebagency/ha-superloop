"""API client for Superloop."""
import logging
import asyncio
import aiohttp
import async_timeout
from typing import Any, Dict, Optional

from .const import (
    API_BASE_URL, 
    API_LOGIN_ENDPOINT, 
    API_GET_SERVICES_ENDPOINT
)

_LOGGER = logging.getLogger(__name__)

class SuperloopApiError(Exception):
    """Exception to indicate an error from the Superloop API."""
    pass

class SuperloopClient:
    """API client for interacting with the Superloop API."""

    def __init__(
        self, 
        username: str = None, 
        password: str = None, 
        session: aiohttp.ClientSession = None,
        access_token: str = None,
        refresh_token: str = None
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token

    def get_access_token(self) -> str:
        """Get the current access token."""
        return self._access_token
        
    def get_refresh_token(self) -> str:
        """Get the current refresh token."""
        return self._refresh_token

    async def authenticate(self) -> bool:
        """Authenticate with the Superloop API."""
        try:
            _LOGGER.debug("Authenticating with Superloop API")
            
            with async_timeout.timeout(30):
                auth_data = {
                    "username": self._username,
                    "password": self._password,
                    "persistLogin": True,
                    "brand": "superloop"
                }
                
                response = await self._session.post(
                    f"{API_BASE_URL}{API_LOGIN_ENDPOINT}",
                    json=auth_data
                )
                
                _LOGGER.debug(f"Authentication response status: {response.status}")
                
                if response.status != 200:
                    _LOGGER.error(f"Authentication failed: {response.status}")
                    response_text = await response.text()
                    _LOGGER.debug(f"Authentication error response: {response_text}")
                    return False
                
                data = await response.json()
                
                # Store tokens
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                
                if not self._access_token:
                    _LOGGER.error("No access token in response")
                    return False
                    
                _LOGGER.debug("Authentication successful")
                return True
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            _LOGGER.error(f"Error authenticating with Superloop API: {error}")
            return False
        except Exception as e:
            _LOGGER.exception(f"Unexpected exception during authentication: {e}")
            return False

    async def get_services(self) -> Dict[str, Any]:
        """Get the services data from the Superloop API."""
        if not self._access_token:
            if not await self.authenticate():
                raise SuperloopApiError("Failed to authenticate with Superloop API")
        
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
                    # Token expired, try to re-authenticate
                    _LOGGER.debug("Token expired, re-authenticating")
                    if await self.authenticate():
                        # Retry with new token
                        headers = {"Authorization": f"Bearer {self._access_token}"}
                        response = await self._session.get(
                            f"{API_BASE_URL}{API_GET_SERVICES_ENDPOINT}",
                            headers=headers
                        )
                        
                        if response.status != 200:
                            response_text = await response.text()
                            _LOGGER.error(f"Error fetching services after reauth: {response.status}, {response_text}")
                            raise SuperloopApiError(f"Failed to get services after reauth: {response.status}")
                    else:
                        raise SuperloopApiError("Failed to re-authenticate with Superloop API")
                
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