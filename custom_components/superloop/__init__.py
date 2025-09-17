import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from homeassistant.core import ServiceCall

from .api import SuperloopClient, SuperloopApiError
from .coordinator import SuperloopCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "superloop"
PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Superloop from a config entry."""
    _LOGGER.debug("Setting up Superloop entry: %s", entry.entry_id)

    data = entry.data
    access_token = data["access_token"]
    refresh_token = data.get("refresh_token")  # None for login-jwt flow
    expires_in = data.get("expires_in")
    expires_at_ms = data.get("expires_at_ms")
    login_method = data.get("login_method")  # "login_jwt" or "legacy_auth" (optional)

    # Build API client (handles both login-jwt and legacy tokens)
    client = SuperloopClient(
        access_token=access_token,
        refresh_token=refresh_token,
        hass=hass,
        entry=entry,
        expires_in=expires_in,
        expires_at_ms=expires_at_ms,
        login_method=login_method,
    )

    # Coordinator drives updates; choose your cadence
    coordinator = SuperloopCoordinator(hass, client, update_interval_minutes=30)

    try:
        await coordinator.async_config_entry_first_refresh()
        await coordinator.async_update_daily_usage()
    except ConfigEntryAuthFailed as err:
        _LOGGER.error("Authentication failed during setup: %s", err)
        raise ConfigEntryAuthFailed from err
    except SuperloopApiError as err:
        _LOGGER.error("Failed to connect to Superloop API: %s", err)
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # === Scheduled Daily Usage Fetch (06:05 local) ===
    async def _schedule_daily_usage(now):
        _LOGGER.debug("Scheduled daily usage fetch triggered")
        await coordinator.async_update_daily_usage()

    hass.async_create_task(coordinator.async_update_daily_usage())

    async_track_time_change(
        hass,
        _schedule_daily_usage,
        hour=6,
        minute=5,
        second=0,
    )

    # === Manual Refresh Data Service ===
    async def async_refresh_data_service(call: ServiceCall) -> None:
        """Handle refresh data service call."""
        _LOGGER.debug("Manual refresh data service called")
        coord = hass.data[DOMAIN].get(entry.entry_id)
        if coord:
            await coord.async_refresh()
            _LOGGER.info("Superloop data refreshed manually")

    # === Manual Refresh Token Service (legacy only) ===
    async def async_refresh_token_service(call: ServiceCall) -> None:
        """Handle manual token refresh."""
        _LOGGER.debug("Manual refresh token service called")
        coord = hass.data[DOMAIN].get(entry.entry_id)
        if not coord:
            _LOGGER.error("Coordinator not found for entry: %s", entry.entry_id)
            return
        try:
            refreshed = await coord.client.async_check_and_refresh_token_if_needed(force=True)
            if refreshed:
                _LOGGER.info("Superloop legacy token refreshed manually")
            else:
                if coord.client.refresh_token is None:
                    _LOGGER.info("Entry uses login-jwt (no refresh token). Reauth required if expired.")
                else:
                    _LOGGER.info("Token not near expiry; no refresh performed.")
        except Exception as err:
            _LOGGER.exception("Failed to manually refresh token: %s", err)

    hass.services.async_register(DOMAIN, "refresh_data", async_refresh_data_service)
    hass.services.async_register(DOMAIN, "refresh_token", async_refresh_token_service)

    # === Silent Token Refresh (every 10 min; no-op for login-jwt) ===
    async def _background_refresh_tokens(now):
        _LOGGER.debug("Background token refresh check…")
        coord = hass.data[DOMAIN].get(entry.entry_id)
        if coord:
            await coord.client.async_check_and_refresh_token_if_needed()

    async_track_time_interval(hass, _background_refresh_tokens, timedelta(minutes=10))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Superloop config entry."""
    _LOGGER.debug("Unloading Superloop entry: %s", entry.entry_id)

    coordinator: SuperloopCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.client.async_close()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok

# === Speed Boost Service ===
async def async_speed_boost_service(call: ServiceCall) -> None:
    """
    Enable a speed boost.
    Service: superloop.speed_boost
    Fields:
      - days: int (default 1)
      - start: string ISO datetime (optional; default now in HA TZ)
      - customer_id: int (optional)
    """
    coord = hass.data[DOMAIN].get(entry.entry_id)
    if not coord:
        _LOGGER.error("Coordinator not found for entry: %s", entry.entry_id)
        return

    days = int(call.data.get("days", 1))
    start_str = call.data.get("start")  # ISO like "2025-09-17T08:30:00+10:00"
    customer_id = call.data.get("customer_id")

    # Parse start (optional)
    start_dt = None
    if start_str:
        from homeassistant.util import dt as dt_util
        start_dt = dt_util.parse_datetime(start_str)
        if start_dt is None:
            _LOGGER.warning("Invalid start datetime '%s'; using now.", start_str)
        else:
            # Ensure timezone-aware in HA TZ
            if start_dt.tzinfo is None:
                start_dt = dt_util.as_local(start_dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))
            else:
                start_dt = dt_util.as_local(start_dt)

    try:
        result = await coord.client.async_enable_speed_boost(start_dt_aware=start_dt, boost_days=days, customer_id=customer_id)
        _LOGGER.info("Speed boost requested: %s", result)
    except ConfigEntryAuthFailed as err:
        _LOGGER.error("Auth failed while enabling speed boost: %s", err)
        # Let the UI prompt reauth on next update
        raise
    except Exception as err:
        _LOGGER.exception("Speed boost request failed: %s", err)

hass.services.async_register(DOMAIN, "speed_boost", async_speed_boost_service)
