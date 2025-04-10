from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfDataRate, UnitOfInformation
from datetime import datetime

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Superloop sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []

    for service in coordinator.data.get('broadband', []):
        service_number = service["serviceNumber"]

        # Existing sensors
        sensors.extend([
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
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Download Speed",
                unique_id=f"superloop-{service_number}-speed",
                unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                icon="mdi:speedometer",
                device_class=None,
                value_key="eveningSpeed"
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Plan",
                unique_id=f"superloop-{service_number}-plan-title",
                unit_of_measurement=None,
                icon="mdi:label",
                device_class=None,
                value_key="planTitle"
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Billing Progress",
                unique_id=f"superloop-{service_number}-billing-progress",
                unit_of_measurement="%",
                icon="mdi:calendar-clock",
                device_class=None,
                state_class="measurement",
                value_key="billingCycleProgressPercentage"
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Plan Evening Speed",
                unique_id=f"superloop-{service_number}-evening-speed",
                unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                icon="mdi:speedometer-medium",
                device_class=None,
                value_key="eveningSpeed"
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Free Download Usage",
                unique_id=f"superloop-{service_number}-free-download",
                unit_of_measurement=UnitOfInformation.GIGABYTES,
                icon="mdi:download",
                device_class="data_size",
                state_class="total_increasing",
                value_key="freeDownload"
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Download Usage",
                unique_id=f"superloop-{service_number}-nonfree-download",
                unit_of_measurement=UnitOfInformation.GIGABYTES,
                icon="mdi:download-off",
                device_class="data_size",
                state_class="total_increasing",
                value_key="nonFreeDownload"
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Free Upload Usage",
                unique_id=f"superloop-{service_number}-free-upload",
                unit_of_measurement=UnitOfInformation.GIGABYTES,
                icon="mdi:upload",
                device_class="data_size",
                state_class="total_increasing",
                value_key="freeUpload"
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Upload Usage",
                unique_id=f"superloop-{service_number}-nonfree-upload",
                unit_of_measurement=UnitOfInformation.GIGABYTES,
                icon="mdi:upload-off",
                device_class="data_size",
                state_class="total_increasing",
                value_key="nonFreeUpload"
            ),
            SuperloopSensor(
                coordinator=coordinator,
                service=service,
                description="Plan Allowance",
                unique_id=f"superloop-{service_number}-plan-allowance",
                unit_of_measurement=None,
                icon="mdi:database",
                device_class=None,
                value_key="allowance"
            ),
        ])

    # ✨ NEW: Daily Usage Sensors
    sensors.extend([
        SuperloopDailySensor(coordinator, "upload"),
        SuperloopDailySensor(coordinator, "download"),
        SuperloopDailySensor(coordinator, "total"),
    ])

    async_add_entities(sensors, True)

class SuperloopSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Superloop regular sensor."""

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

        try:
            usage_summary = current_service.get("usageSummary", {})

            if self._value_key.startswith("usageSummary."):
                key = self._value_key.split(".")[1]
                return round(usage_summary.get(key, 0) / 1_000_000_000, 2)

            if self._value_key in ("freeDownload", "nonFreeDownload", "freeUpload", "nonFreeUpload"):
                return round(usage_summary.get(self._value_key, 0) / 1_000_000_000, 2)

            if self._value_key == "eveningSpeed":
                speed_text = current_service.get("eveningSpeed", "")
                return int(speed_text.split(" ")[0]) if speed_text else None

            if self._value_key == "billingCycleProgressPercentage":
                return current_service.get("billingCycleProgressPercentage", None)

            if self._value_key == "planTitle":
                return current_service.get("planTitle", None)

            if self._value_key == "allowance":
                return current_service.get("allowance", None)

        except Exception as e:
            _LOGGER.error("Error parsing Superloop sensor value: %s", e)
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

class SuperloopDailySensor(CoordinatorEntity, SensorEntity):
    """Representation of Superloop Daily Upload/Download/Total usage."""

    def __init__(self, coordinator, sensor_type):
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_icon = "mdi:chart-line"
        self._attr_device_class = "data_size"
        self._attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
        self._attr_state_class = "total"
        self._last_reset = None

        if sensor_type == "upload":
            self._attr_name = "Superloop Daily Upload Usage"
            self._attr_unique_id = "superloop-daily-upload-usage"
        elif sensor_type == "download":
            self._attr_name = "Superloop Daily Download Usage"
            self._attr_unique_id = "superloop-daily-download-usage"
        elif sensor_type == "total":
            self._attr_name = "Superloop Daily Total Usage"
            self._attr_unique_id = "superloop-daily-total-usage"

    @property
    def native_value(self):
        """Return yesterday's upload/download/total GB usage."""
        daily = self.coordinator.daily_usage
        if not daily or "usageDaily" not in daily:
            return None
        yesterday = daily["usageDaily"][0]
        try:
            # Set _last_reset from yesterday date
            if not self._last_reset:
                date_obj = datetime.strptime(yesterday[0], "%d %b %Y")
                self._last_reset = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)

            if self._sensor_type == "upload":
                value = yesterday[1].replace("GB", "").strip()
            elif self._sensor_type == "download":
                value = yesterday[2].replace("GB", "").strip()
            elif self._sensor_type == "total":
                value = yesterday[3].replace("GB", "").strip()

            return float(value)
        except (IndexError, ValueError):
            return None

    @property
    def last_reset(self):
        return self._last_reset