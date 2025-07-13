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
        if not self._session.closed:
            await self._session.close()

    def _build_headers(self):
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Origin": "https://superhub.superloop.com",
            "Referer": "https://superhub.superloop.com",
        }

    async def async_get_services(self):
        headers = self._build_headers()
        _LOGGER.debug("Fetching services with access token: %s...", self._access_token[:10] if self._access_token else None)

        try:
            async with async_timeout.timeout(30):
                _LOGGER.debug("Making GET request to %s", f"{BASE_API_URL}/getServices/")
                response = await self._session.get(f"{BASE_API_URL}/getServices/", headers=headers)
                status = response.status
                _LOGGER.debug("Superloop API getServices status: %s", status)

                if status in [401, 403]:
                    _LOGGER.warning("Access token expired or unauthorized (HTTP %s), trying to refresh...", status)
                    try:
                        await self._try_refresh_token()
                    except ConfigEntryAuthFailed as err:
                        _LOGGER.error("Failed to refresh token, raising auth failed.")
                        raise ConfigEntryAuthFailed("Token refresh failed") from err

                    headers = self._build_headers()
                    _LOGGER.debug("Retrying GET request with new token: %s...", self._access_token[:10] if self._access_token else None)
                    response = await self._session.get(f"{BASE_API_URL}/getServices/", headers=headers)
                    status = response.status
                    _LOGGER.debug("Retry getServices status: %s", status)

                    if status in [401, 403]:
                        _LOGGER.error("Still getting %s after token refresh, triggering reauthentication.", status)
                        raise ConfigEntryAuthFailed("Superloop token invalid after refresh")

                if status != 200:
                    response_text = await response.text()
                    _LOGGER.error("Failed to fetch services: HTTP %s, Response: %s", status, response_text[:200])
                    raise SuperloopApiError(f"Failed to fetch services: HTTP {status}")

                data = await response.json()
                _LOGGER.debug("Service response data: %s", data)
                return data

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout fetching services")
            raise SuperloopApiError("Timeout fetching services") from ex
        except Exception as ex:
            _LOGGER.exception("Unexpected error fetching services: %s", str(ex))
            raise

    async def async_get_daily_usage(self, service_id: int):
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
        payload = {
            "refresh_token": self._refresh_token
        }

        _LOGGER.debug("Sending refresh payload to %s", REFRESH_URL)

        try:
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = aiohttp.ClientSession()

            async with async_timeout.timeout(10):
                _LOGGER.debug("Making token refresh POST request")
                response = await self._session.post(REFRESH_URL, json=payload)
                status = response.status
                resp_text = await response.text()

                _LOGGER.debug("Token refresh HTTP status: %s", status)
                _LOGGER.debug("Token refresh response body (first 100 chars): %s...", resp_text[:100])

                if status == 401:
                    _LOGGER.error("Refresh token invalid, received 401 Unauthorized.")
                    raise ConfigEntryAuthFailed("Superloop refresh token invalid (401 Unauthorized)")

                if status != 200:
                    _LOGGER.error("Failed to refresh token (HTTP %s)", status)
                    raise SuperloopApiError(f"Failed to refresh token: HTTP {status}")

                try:
                    data = await response.json()
                    _LOGGER.debug("Parsed token refresh response keys: %s", list(data.keys()))

                    old_access_token = self._access_token
                    self._access_token = data["access_token"]
                    self._refresh_token = data["refresh_token"]
                    expires_in = data.get("expires_in", 14400)
                    expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
                    self._token_expiry_time = expiry_time

                    _LOGGER.info(
                        "Token refreshed successfully.\n"
                        "Old token: %s...\nNew token: %s...\nExpires in: %s seconds (at UTC %s)",
                        old_access_token[:10] if old_access_token else None,
                        self._access_token[:10] if self._access_token else None,
                        expires_in,
                        expiry_time.isoformat()
                    )

                    self._hass.config_entries.async_update_entry(
                        self._entry,
                        data={
                            "access_token": self._access_token,
                            "refresh_token": self._refresh_token,
                            "expires_in": expires_in,
                        }
                    )

                    # ✅ Force reload to apply updated client everywhere
                    await self._hass.config_entries.async_reload(self._entry.entry_id)

                except Exception as json_ex:
                    _LOGGER.exception("Failed to parse refresh token response JSON: %s", str(json_ex))
                    raise SuperloopApiError(f"Failed to parse refresh token response: {str(json_ex)}")

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout refreshing token")
            raise SuperloopApiError("Timeout refreshing token")
        except Exception as ex:
            _LOGGER.exception("Unexpected error during token refresh: %s", str(ex))
            raise

    async def async_check_and_refresh_token_if_needed(self, force=False):
        now = datetime.utcnow()

        if self._token_expiry_time is None:
            _LOGGER.warning("Token expiry time not set, skipping silent refresh check.")
            if force:
                _LOGGER.info("Force refresh requested, attempting to refresh token.")
                try:
                    await self._try_refresh_token()
                    return True
                except Exception as ex:
                    _LOGGER.error("Force refresh failed: %s", str(ex))
                    return False
            return False

        time_remaining = self._token_expiry_time - now
        _LOGGER.debug("Token expiry check: %s minutes remaining until token expires", 
                      time_remaining.total_seconds() / 60)

        if force or time_remaining < timedelta(minutes=210):
            if force:
                _LOGGER.info("Forced token refresh requested")
            else:
                _LOGGER.info("Access token nearing expiry (%s minutes remaining), refreshing proactively.", 
                             time_remaining.total_seconds() / 60)
            try:
                await self._try_refresh_token()
                return True
            except ConfigEntryAuthFailed:
                _LOGGER.error("Token refresh failed, reauthentication needed.")
                return False
            except Exception as ex:
                _LOGGER.exception("Unexpected error during token refresh: %s", str(ex))
                return False

        return False

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token
