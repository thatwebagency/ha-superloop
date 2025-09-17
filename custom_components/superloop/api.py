import logging
import aiohttp
import async_timeout
import asyncio
import base64
import json
import time
from datetime import datetime, timedelta
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

BASE_API_URL = "https://webservices.myexetel.exetel.com.au/api"
REFRESH_URL  = "https://webservices.myexetel.exetel.com.au/api/auth/token/refresh"
SPEED_BOOST_BASE = "https://webservices-api.superloop.com/v1"
REFRESH_SKEW_SEC = 10 * 60  # refresh when <10 min remaining (legacy flow)

class SuperloopApiError(Exception):
    """General Superloop API exception."""
    pass

def _jwt_payload(token: str) -> dict | None:
    """Best-effort decode of a JWT payload (no verification)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        b64 = parts[1]
        pad = "=" * (-len(b64) % 4)
        return json.loads(base64.urlsafe_b64decode(b64 + pad).decode("utf-8"))
    except Exception:
        return None
    
def _jwt_customer_id(token: str) -> int | None:
    """Extract customer_id from current JWT (Exetel token)."""
    try:
        import json, base64
        p = token.split(".")[1]
        pad = "=" * (-len(p) % 4)
        data = json.loads(base64.urlsafe_b64decode(p + pad).decode("utf-8"))
        return int(data.get("customer_id")) if data.get("customer_id") is not None else None
    except Exception:
        return None

class SuperloopClient:
    """
    Works with both:
      - login-jwt tokens (long-lived, no refresh token, no MFA)
      - legacy tokens (4h + refresh_token, MFA outside this client)
    """
    def __init__(
        self,
        access_token: str,
        refresh_token: str | None,
        hass,
        entry,
        expires_in: int | None = None,
        expires_at_ms: int | None = None,
        login_method: str | None = None,  # "login_jwt" or "legacy_auth"
    ):
        self._hass = hass
        self._entry = entry
        self._session: aiohttp.ClientSession = async_get_clientsession(hass)
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._login_method = login_method or entry.data.get("login_method")  # best effort

        now_ms = int(time.time() * 1000)
        if expires_at_ms:
            self._expires_at_ms = int(expires_at_ms)
        elif expires_in is not None:
            self._expires_at_ms = now_ms + int(expires_in) * 1000
        else:
            payload = _jwt_payload(access_token)
            self._expires_at_ms = payload["exp"] * 1000 if payload and "exp" in payload else None

        _LOGGER.debug(
            "SuperloopClient init: method=%s exp=%s",
            self._login_method or "unknown",
            datetime.utcfromtimestamp(self._expires_at_ms/1000).isoformat() if self._expires_at_ms else "unknown",
        )

    async def async_close(self):
        # Do not close HA-shared session
        pass

    def _build_headers(self):
        return { "Authorization": f"Bearer {self._access_token}" }

    async def _ensure_valid(self):
        """
        For legacy tokens: proactively refresh close to expiry.
        For login-jwt: nothing to do (no refresh endpoint); handle 401 at call time.
        """
        if not self._expires_at_ms:
            return
        if not self._refresh_token:
            # login-jwt (typically no refresh token) → nothing proactive
            return

        now_ms = int(time.time() * 1000)
        if now_ms >= self._expires_at_ms - REFRESH_SKEW_SEC * 1000:
            _LOGGER.debug("Proactively refreshing legacy token (%.0fs left)",
                          (self._expires_at_ms - now_ms)/1000)
            await self._try_refresh_token()

    async def async_get_services(self):
        await self._ensure_valid()
        headers = self._build_headers()
        url = f"{BASE_API_URL}/getServices/"

        try:
            async with async_timeout.timeout(30):
                resp = await self._session.get(url, headers=headers)

                if resp.status in (401, 403):
                    # Legacy: try one refresh then retry once
                    if self._refresh_token:
                        _LOGGER.warning("Unauthorized (%s). Trying refresh → retry…", resp.status)
                        await self._try_refresh_token()
                        headers = self._build_headers()
                        resp = await self._session.get(url, headers=headers)
                    # login-jwt or still failing → raise for reauth
                    if resp.status in (401, 403):
                        text = (await resp.text())[:200]
                        _LOGGER.error("getServices unauthorized after refresh (if any): %s", text)
                        raise ConfigEntryAuthFailed("Token invalid or requires reauth")

                if resp.status != 200:
                    text = (await resp.text())[:200]
                    _LOGGER.error("getServices failed HTTP %s: %s", resp.status, text)
                    raise SuperloopApiError(f"getServices: HTTP {resp.status}")

                data = await resp.json()
                _LOGGER.debug("getServices OK")
                return data

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout fetching services")
            raise SuperloopApiError("Timeout fetching services") from ex
        except ConfigEntryAuthFailed:
            raise
        except Exception as ex:
            _LOGGER.exception("Unexpected error fetching services: %s", ex)
            raise

    async def async_get_daily_usage(self, service_id: int):
        await self._ensure_valid()
        headers = self._build_headers()
        url = f"{BASE_API_URL}/getBroadbandDailyUsage/{service_id}"

        try:
            async with async_timeout.timeout(40):
                resp = await self._session.get(url, headers=headers)

                if resp.status in (401, 403):
                    if self._refresh_token:
                        _LOGGER.warning("Unauthorized during daily usage. Refresh → retry…")
                        await self._try_refresh_token()
                        headers = self._build_headers()
                        resp = await self._session.get(url, headers=headers)
                    if resp.status in (401, 403):
                        text = (await resp.text())[:200]
                        _LOGGER.error("daily usage unauthorized after refresh: %s", text)
                        raise ConfigEntryAuthFailed("Token invalid or requires reauth")

                if resp.status != 200:
                    text = (await resp.text())[:200]
                    _LOGGER.error("daily usage failed HTTP %s: %s", resp.status, text)
                    raise SuperloopApiError(f"daily usage: HTTP {resp.status}")

                data = await resp.json()
                _LOGGER.debug("daily usage OK")
                return data

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout fetching daily usage")
            raise SuperloopApiError("Timeout fetching daily usage") from ex
        except ConfigEntryAuthFailed:
            raise
        except Exception as ex:
            _LOGGER.exception("Unexpected error fetching daily usage: %s", ex)
            raise

    async def _try_refresh_token(self):
        """
        Legacy-only. If no refresh token is present (login-jwt flow), raise for reauth instead of looping.
        """
        if not self._refresh_token:
            _LOGGER.error("No refresh token available; cannot refresh. Reauth required.")
            raise ConfigEntryAuthFailed("No refresh token (login-jwt). Reauthenticate.")

        payload = { "refresh_token": self._refresh_token }
        _LOGGER.debug("POST %s (refresh)", REFRESH_URL)

        async with async_timeout.timeout(15):
            resp = await self._session.post(REFRESH_URL, json=payload)
            sample = (await resp.text())[:200]

        _LOGGER.debug("Refresh HTTP %s, body: %s…", resp.status, sample)
        if resp.status == 401:
            raise ConfigEntryAuthFailed("Refresh token invalid (401)")
        if resp.status != 200:
            raise SuperloopApiError(f"Refresh failed HTTP {resp.status}")

        data = await resp.json()

        new_access = data["access_token"]
        new_refresh = data.get("refresh_token") or self._refresh_token
        expires_in  = int(data.get("expires_in", 14400))

        # Prefer JWT exp when present
        payload = _jwt_payload(new_access)
        if payload and "exp" in payload:
            self._expires_at_ms = int(payload["exp"]) * 1000
        else:
            self._expires_at_ms = int(time.time() * 1000) + expires_in * 1000

        self._access_token  = new_access
        self._refresh_token = new_refresh

        _LOGGER.info(
            "Legacy token refreshed. exp=%s head=%s…",
            datetime.utcfromtimestamp(self._expires_at_ms/1000).isoformat(),
            new_access[:16],
        )

        # Persist back to config entry (merge, don't clobber)
        self._hass.config_entries.async_update_entry(
            self._entry,
            data={
                **self._entry.data,
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "expires_at_ms": self._expires_at_ms,
                "expires_in": expires_in,
                "login_method": self._login_method or self._entry.data.get("login_method") or "legacy_auth",
            },
        )

    async def async_enable_speed_boost(
        self,
        start_dt_aware=None,
        boost_days: int = 1,
        service_id: int | None = None,
    ):
        await self._ensure_valid()

        # pick service_id if not passed: prefer ACTIVE service
        if service_id is None:
            services = await self.async_get_services()
            bb = services.get("broadband") or []
            if not bb:
                raise SuperloopApiError("No broadband services available for speed boost")
            service = next((s for s in bb if (s.get("status") or "").upper() == "ACTIVE"), bb[0])
            service_id = service.get("id")
            if not service_id:
                raise SuperloopApiError("Could not determine service_id for speed boost")

        # time handling (HA local tz) → "YYYY-MM-DD HH:MM:SS"
        from homeassistant.util import dt as dt_util
        if start_dt_aware is None:
            start_dt_aware = dt_util.now()
        start_str = start_dt_aware.strftime("%Y-%m-%d %H:%M:%S")

        url = f"{SPEED_BOOST_BASE}/speed-boost/{service_id}"
        headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}
        payload = {"startDate": start_str, "boostDays": int(boost_days)}

        async with async_timeout.timeout(20):
            resp = await self._session.post(url, json=payload, headers=headers)
            text = await resp.text()

        if resp.status in (401, 403):
            if self._refresh_token:
                await self._try_refresh_token()
                headers["Authorization"] = f"Bearer {self._access_token}"
                async with async_timeout.timeout(20):
                    resp = await self._session.post(url, json=payload, headers=headers)
                    text = await resp.text()
            if resp.status in (401, 403):
                raise ConfigEntryAuthFailed(f"Speed boost unauthorized: {text[:200]}")

        if resp.status == 404:
            # most common cause: wrong ID (customer_id instead of service_id)
            raise SuperloopApiError(
                "Speed boost endpoint returned 404 (Resource not found). "
                "Make sure you are using the SERVICE ID, not the customer id."
            )
        if resp.status >= 300:
            raise SuperloopApiError(f"Speed boost failed HTTP {resp.status}: {text[:200]}")

        try:
            return await resp.json()
        except Exception:
            return {"status": "ok", "raw": text[:200]}

    async def async_get_speed_boost_status(self, service_id: int) -> dict:
        headers = self._build_headers()
        url = f"{SPEED_BOOST_BASE}/speed-boost/{service_id}"
        async with async_timeout.timeout(15):
           resp = await self._session.get(url, headers=headers)
        if resp.status == 401:
           await self._try_refresh_token()
           headers = self._build_headers()
        async with async_timeout.timeout(15):
                resp = await self._session.get(url, headers=headers)
        if resp.status != 200:
            raise SuperloopApiError(f"speed-boost status HTTP {resp.status}")
        return await resp.json()  # expect { ..., "boostStatus": "Active"|"Inactive"|"Pending", ... }

    async def async_get_speed_boost_history(self, service_id: int) -> list[dict]:
        headers = self._build_headers()
        url = f"{SPEED_BOOST_BASE}/speed-boost/{service_id}/history"
        async with async_timeout.timeout(15):
            resp = await self._session.get(url, headers=headers)
        if resp.status == 401:
            await self._try_refresh_token()
            headers = self._build_headers()
            async with async_timeout.timeout(15):
                resp = await self._session.get(url, headers=headers)
        if resp.status != 200:
            raise SuperloopApiError(f"speed-boost history HTTP {resp.status}")
        data = await resp.json()
         # UI expects objects with boostDays, startDate, endDate
        return data.get("data", data)
    
    async def async_check_and_refresh_token_if_needed(self, force: bool = False):
        """
        Public hook if a platform wants to nudge a refresh.
        - For login-jwt: does nothing (no refresh); returns False unless force, then raises reauth.
        - For legacy: refreshes when near expiry or when force=True.
        """
        # login-jwt path: no refresh token
        if not self._refresh_token:
            if force:
                _LOGGER.info("Force requested but no refresh token; reauth required.")
                raise ConfigEntryAuthFailed("Reauthenticate (login-jwt expired/revoked)")
            return False

        # legacy path
        now_ms = int(time.time() * 1000)
        secs_left = ((self._expires_at_ms - now_ms) / 1000) if self._expires_at_ms else None
        _LOGGER.debug("Token expiry check (legacy): %s seconds left", f"{secs_left:.0f}" if secs_left is not None else "unknown")

        if force or (secs_left is not None and secs_left <= REFRESH_SKEW_SEC):
            try:
                await self._try_refresh_token()
                return True
            except ConfigEntryAuthFailed:
                _LOGGER.error("Refresh failed; reauth needed")
                return False
        return False

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    @property
    def expires_at_ms(self) -> int | None:
        return self._expires_at_ms
