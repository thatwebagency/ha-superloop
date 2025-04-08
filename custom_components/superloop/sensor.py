import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfDataRate, PERCENTAGE

from .api import SuperloopClient, SuperloopApiError
from .coordinator import SuperloopCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "superloop"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Superloop sensors."""
    coordinator: SuperloopCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        SuperloopTotalUsageSensor(coordinator),
        SuperloopBillingProgressSensor(coordinator),
        SuperloopPlanNameSensor(coordinator),
        SuperloopEveningSpeedSensor(coordinator),
    ]

    async_add_entities(entities)

class SuperloopSensor(CoordinatorEntity, Entity):
    """Base class for a Superloop sensor."""

    def __init__(self, coordinator: SuperloopCoordinator, name: str, unique_id: str):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id

class SuperloopTotalUsageSensor(SuperloopSensor):
    """Sensor for total usage this billing cycle."""

    def __init__(self, coordinator: SuperloopCoordinator):
        super().__init__(coordinator, "Superloop Total Usage", "superloop_total_usage")

    @property
    def native_value(self):
        broadband = self._get_first_broadband()
        return broadband.get("usageSummary", {}).get("total") if broadband else None

class SuperloopBillingProgressSensor(SuperloopSensor):
    """Sensor for billing cycle progress."""

    def __init__(self, coordinator: SuperloopCoordinator):
        super().__init__(coordinator, "Superloop Billing Progress", "superloop_billing_progress")
        self._attr_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self):
        broadband = self._get_first_broadband()
        return broadband.get("billingCycleProgressPercentage") if broadband else None

class SuperloopPlanNameSensor(SuperloopSensor):
    """Sensor for the plan name."""

    def __init__(self, coordinator: SuperloopCoordinator):
        super().__init__(coordinator, "Superloop Plan Name", "superloop_plan_name")

    @property
    def native_value(self):
        broadband = self._get_first_broadband()
        return broadband.get("planTitle") if broadband else None

class SuperloopEveningSpeedSensor(SuperloopSensor):
    """Sensor for evening speed."""

    def __init__(self, coordinator: SuperloopCoordinator):
        super().__init__(coordinator, "Superloop Evening Speed", "superloop_evening_speed")
        self._attr_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND

    @property
    def native_value(self):
        broadband = self._get_first_broadband()
        evening_speed = broadband.get("eveningSpeed") if broadband else None
        if evening_speed and " Mbps" in evening_speed:
            return int(evening_speed.replace(" Mbps", ""))
        return None

    def _get_first_broadband(self):
        services = self.coordinator.data
        if services and services.get("broadband"):
            return services["broadband"][0]
        return None
