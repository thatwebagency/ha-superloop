from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfInformation

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []

    for service in coordinator.data.get('broadband', []):
        service_number = service["serviceNumber"]

        # Existing Sensors
        sensors.append(
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Data Usage",
                unique_id=f"superloop-{service_number}-usage",
                unit_of_measurement=UnitOfInformation.GIGABYTES,
                icon="mdi:download-network",
                device_class="data_size",
                state_class="total_increasing",
                value_key="usageSummary.totalBytes"
            )
        )

        # (Other regular sensors skipped for brevity...)

    # ⏳ Defer daily usage sensors to AFTER first daily data fetched
    async def async_setup_daily_sensors():
        if coordinator.daily_usage:
            _LOGGER.debug("Setting up Superloop Daily Usage sensors...")
            async_add_entities([
                SuperloopDailyUploadSensor(coordinator),
                SuperloopDailyDownloadSensor(coordinator),
                SuperloopDailyTotalSensor(coordinator),
            ], True)

    coordinator.async_add_listener(async_setup_daily_sensors)
    
    async_add_entities(sensors, True)

class SuperloopSensor(CoordinatorEntity, SensorEntity):
    """Representation of a regular Superloop sensor."""

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
        self._value_key = value_key

    @property
    def native_value(self):
        """Return the current value."""
        service_number = self._service["serviceNumber"]
        broadband_services = self.coordinator.data.get("broadband", [])
        current_service = next((s for s in broadband_services if s["serviceNumber"] == service_number), None)

        if not current_service:
            return None

        if self._value_key == "usageSummary.totalBytes":
            return round(current_service.get("usageSummary", {}).get("totalBytes", 0) / (1024 ** 3), 2)

        return None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._service["serviceNumber"])},
            "name": "Superloop Service",
            "manufacturer": "Superloop",
            "model": self._service.get("planTitle", "Broadband Service"),
            "entry_type": "service",
        }

class SuperloopDailyUploadSensor(CoordinatorEntity, SensorEntity):
    """Daily Upload Usage Sensor."""

    _attr_name = "Superloop Daily Upload Usage"
    _attr_unique_id = "superloop-daily-upload"
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
    _attr_icon = "mdi:upload"
    _attr_device_class = "data_size"

    def __init__(self, coordinator):
        super().__init__(coordinator)

    @property
    def native_value(self):
        """Return today's upload GB."""
        daily = self.coordinator.daily_usage
        if not daily or "usageDaily" not in daily:
            return None
        today = daily["usageDaily"][0]
        upload = today[1].replace("GB", "").strip()
        return float(upload)

class SuperloopDailyDownloadSensor(CoordinatorEntity, SensorEntity):
    """Daily Download Usage Sensor."""

    _attr_name = "Superloop Daily Download Usage"
    _attr_unique_id = "superloop-daily-download"
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
    _attr_icon = "mdi:download"
    _attr_device_class = "data_size"

    def __init__(self, coordinator):
        super().__init__(coordinator)

    @property
    def native_value(self):
        """Return today's download GB."""
        daily = self.coordinator.daily_usage
        if not daily or "usageDaily" not in daily:
            return None
        today = daily["usageDaily"][0]
        download = today[2].replace("GB", "").strip()
        return float(download)

class SuperloopDailyTotalSensor(CoordinatorEntity, SensorEntity):
    """Daily Total Usage Sensor."""

    _attr_name = "Superloop Daily Total Usage"
    _attr_unique_id = "superloop-daily-total"
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
    _attr_icon = "mdi:chart-line"
    _attr_device_class = "data_size"

    def __init__(self, coordinator):
        super().__init__(coordinator)

    @property
    def native_value(self):
        """Return today's total usage GB."""
        daily = self.coordinator.daily_usage
        if not daily or "usageDaily" not in daily:
            return None
        today = daily["usageDaily"][0]
        total = today[3].replace("GB", "").strip()
        return float(total)
