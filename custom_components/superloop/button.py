import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from . import DOMAIN
from .coordinator import SuperloopCoordinator

_LOGGER = logging.getLogger(__name__)

def _pick_service(services_data: dict) -> dict | None:
    """Prefer ACTIVE broadband service; otherwise first."""
    bb = (services_data or {}).get("broadband") or []
    if not bb:
        return None
    return next((s for s in bb if (s.get("status") or "").upper() == "ACTIVE"), bb[0])

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coord: SuperloopCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SuperloopSpeedBoostButton(coord, entry)], update_before_add=False)

class SuperloopSpeedBoostButton(ButtonEntity):
    """One-shot button: triggers Speed Boost now for 1 day."""

    _attr_has_entity_name = True
    _attr_name = "Enable Speed Boost"
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator: SuperloopCoordinator, entry: ConfigEntry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}-speed-boost-button"
        # Group under the Superloop device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or "Superloop",
            manufacturer="Superloop",
            model="Superhub API",
        )

    async def async_press(self) -> None:
        """Trigger a 1-day speed boost starting now."""
        services = self.coordinator.data or {}
        svc = _pick_service(services)
        if not svc or not svc.get("id"):
            _LOGGER.warning("No broadband service found to boost.")
            return

        service_id = svc["id"]
        try:
            result = await self.coordinator.client.async_enable_speed_boost(
                service_id=service_id,
                boost_days=1,
                start_dt_aware=None,  # now (HA local tz)
            )
            _LOGGER.info("Speed boost requested for service_id=%s: %s", service_id, result)
            # Optional: refresh to pull latest boost status
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.exception("Speed boost request failed: %s", err)
