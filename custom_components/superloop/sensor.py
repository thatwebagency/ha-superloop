from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import DATA_RATE_MEGABITS_PER_SECOND, DATA_SIZE_GIGABYTES

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []

    for service in coordinator.data.get('broadband', []):
        service_number = service["serviceNumber"]

        # Usage sensor
        sensors.append(
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Data Usage",
                unique_id=f"superloop-{service_number}-usage",
                unit_of_measurement=DATA_SIZE_GIGABYTES,
                icon="mdi:download-network",
                device_class="data_size",
                state_class="total_increasing",
                value_key="usageSummary.total"
            )
        )

        # Speed sensor
        sensors.append(
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Download Speed",
                unique_id=f"superloop-{service_number}-speed",
                unit_of_measurement=DATA_RATE_MEGABITS_PER_SECOND,
                icon="mdi:speedometer",
                device_class="speed",
                value_key="eveningSpeedValue"
            )
        )

    async_add_entities(sensors, True)

class SuperloopSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Superloop Sensor."""

    def __init__(self, coordinator, service, description, unique_id, unit_of_measurement, icon, device_class, value_key, state_class=None):
        super().__init__(coordinator)
        self._service = service
        self._description = description
        self._attr_name = f"Superloop {description}"
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._value_key = value_key  # key path to the data we want

    @property
    def native_value(self):
        """Return the current value based on the latest coordinator data."""
        # Dynamically extract the correct value every time
        service_number = self._service["serviceNumber"]

        # Get the latest broadband service data
        broadband_services = self.coordinator.data.get("broadband", [])
        current_service = next((s for s in broadband_services if s["serviceNumber"] == service_number), None)

        if not current_service:
            return None

        if self._value_key == "usageSummary.total":
            return round(current_service.get("usageSummary", {}).get("totalBytes", 0) / (1024 ** 3), 2)  # Convert Bytes to GB
        if self._value_key == "eveningSpeedValue":
            try:
                return int(current_service.get("eveningSpeed", "").split(" ")[0])
            except Exception:
                return None

        return None

    @property
    def device_info(self):
        """Return the device info for grouping sensors."""
        return {
            "identifiers": {(DOMAIN, self._service["serviceNumber"])},
            "name": "Superloop Service",
            "manufacturer": "Superloop",
            "model": self._service.get("planTitle", "Broadband Service"),
            "entry_type": "service",
        }
