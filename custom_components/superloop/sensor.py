from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE, UnitOfDataRate

from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Superloop sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        SuperloopTotalUsageSensor(coordinator),
        SuperloopBillingProgressSensor(coordinator),
        SuperloopPlanNameSensor(coordinator),
        SuperloopEveningSpeedSensor(coordinator),
    ]

    async_add_entities(entities)

class SuperloopTotalUsageSensor(CoordinatorEntity):
    """Sensor for total broadband usage."""

    _attr_name = "Superloop Total Usage"
    _attr_icon = "mdi:download"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"superloop_total_usage"

    @property
    def native_value(self):
        broadband = self._get_first_broadband()
        if broadband and "usageSummary" in broadband:
            return broadband["usageSummary"].get("total")
        return None

    def _get_first_broadband(self):
        services = self.coordinator.data
        if isinstance(services, dict) and services.get("broadband"):
            return services["broadband"][0]
        return None

class SuperloopBillingProgressSensor(CoordinatorEntity):
    """Sensor for billing cycle progress."""

    _attr_name = "Superloop Billing Progress"
    _attr_icon = "mdi:calendar-clock"
    _attr_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"superloop_billing_progress"

    @property
    def native_value(self):
        broadband = self._get_first_broadband()
        if broadband:
            return broadband.get("billingCycleProgressPercentage")
        return None

    def _get_first_broadband(self):
        services = self.coordinator.data
        if isinstance(services, dict) and services.get("broadband"):
            return services["broadband"][0]
        return None

class SuperloopPlanNameSensor(CoordinatorEntity):
    """Sensor for plan name."""

    _attr_name = "Superloop Plan Name"
    _attr_icon = "mdi:file-document-edit"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"superloop_plan_name"

    @property
    def native_value(self):
        broadband = self._get_first_broadband()
        if broadband:
            return broadband.get("planTitle")
        return None

    def _get_first_broadband(self):
        services = self.coordinator.data
        if isinstance(services, dict) and services.get("broadband"):
            return services["broadband"][0]
        return None

class SuperloopEveningSpeedSensor(CoordinatorEntity):
    """Sensor for evening speed."""

    _attr_name = "Superloop Evening Speed"
    _attr_icon = "mdi:speedometer"
    _attr_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"superloop_evening_speed"

    @property
    def native_value(self):
        broadband = self._get_first_broadband()
        if broadband:
            evening_speed = broadband.get("eveningSpeed")
            if evening_speed and " Mbps" in evening_speed:
                return int(evening_speed.replace(" Mbps", ""))
        return None

    def _get_first_broadband(self):
        services = self.coordinator.data
        if isinstance(services, dict) and services.get("broadband"):
            return services["broadband"][0]
        return None
