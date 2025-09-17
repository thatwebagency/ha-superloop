import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from . import DOMAIN
from .coordinator import SuperloopCoordinator

_LOGGER = logging.getLogger(__name__)

def _pick_service(services_data: dict) -> dict | None:
    bb = (services_data or {}).get("broadband") or []
    if not bb:
        return None
    return next((s for s in bb if (s.get("status") or "").upper() == "ACTIVE"), bb[0])

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coord: SuperloopCoordinator = hass.data[DOMAIN][entry.entry_id]
    service = _pick_service(coord.data or {})
    if not service:
        _LOGGER.warning("Superloop button: no broadband service found; not creating button.")
        return
    async_add_entities([SuperloopSpeedBoostButton(coord, entry, service)], update_before_add=False)

class SuperloopSpeedBoostButton(ButtonEntity):
    """One-shot button: triggers Speed Boost now for 1 day."""

    _attr_has_entity_name = True
    _attr_name = "Enable Speed Boost"
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator: SuperloopCoordinator, entry: ConfigEntry, service: dict):
        self.coordinator = coordinator
        self.entry = entry
        self._service = service

        # Keep entity unique_id stable but tie to serviceNumber
        svc_num = service.get("serviceNumber", "unknown")
        self._attr_unique_id = f"{entry.entry_id}-speed-boost-button-{svc_num}"

        # 🔗 IMPORTANT: use the SAME identifiers as your sensors do
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, svc_num)},
            name="Superloop Service",
            manufacturer="Superloop",
            model=service.get("planTitle", "Broadband Service"),
        )

    async def async_press(self) -> None:
        """Trigger a 1-day speed boost starting now."""
        service_id = self._service.get("id")
        if not service_id:
            _LOGGER.warning("Superloop button: service has no id; aborting.")
            return
        try:
            result = await self.coordinator.client.async_enable_speed_boost(
                service_id=service_id,
                boost_days=1,
                start_dt_aware=None,  # now (HA local tz)
            )
            _LOGGER.info("Speed boost requested for service_id=%s: %s", service_id, result)
            # Optionally refresh to update status sensor
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.exception("Speed boost request failed: %s", err)
