from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []

    # Create a sensor for each broadband service
    for service in coordinator.data.get('broadband', []):
        sensors.append(
            SuperloopSensor(
                coordinator,
                service,
                "Usage",
                f"superloop_{service['serviceNumber']}_usage",
                "GB",
                "mdi:download-network",
                service["usageSummary"]["summaryText"],
            )
        )

        sensors.append(
            SuperloopSensor(
                coordinator,
                service,
                "Speed",
                f"superloop_{service['serviceNumber']}_speed",
                "Mbps",
                "mdi:speedometer",
                service["eveningSpeed"].split(" ")[0],  # "811 Mbps" -> "811"
            )
        )

    async_add_entities(sensors, True)

class SuperloopSensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator, service, sensor_type, unique_id, unit_of_measurement, icon, value):
        super().__init__(coordinator)
        self._service = service
        self._sensor_type = sensor_type
        self._attr_unique_id = unique_id
        self._attr_name = f"Superloop {sensor_type} ({service['serviceNumber']})"
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_icon = icon
        self._value = value

    @property
    def native_value(self):
        return self._value

    async def async_update(self):
        await self.coordinator.async_request_refresh()