"""Sensor platform for Superloop integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DATA_GIGABYTES,
    DATA_MEGABITS_PER_SECOND,
    SENSOR_TYPE_DATA_USED,
    SENSOR_TYPE_DATA_REMAINING,
    SENSOR_TYPE_DATA_LIMIT,
    SENSOR_TYPE_DAYS_REMAINING,
    SENSOR_TYPE_PLAN_SPEED,
    SENSOR_TYPE_BILLING_CYCLE_START,
    SENSOR_TYPE_BILLING_CYCLE_END,
)
from .coordinator import SuperloopDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Superloop sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Parse the first service to extract relevant data
    if not coordinator.data or "services" not in coordinator.data or not coordinator.data["services"]:
        _LOGGER.error("No services found in Superloop data")
        return

    service = coordinator.data["services"][0]  # Assuming we want the first service
    
    entities = [
        SuperloopSensor(
            coordinator,
            SENSOR_TYPE_DATA_USED,
            "Data Used",
            "mdi:download",
            DATA_GIGABYTES,
            SensorStateClass.MEASUREMENT,
        ),
        SuperloopSensor(
            coordinator,
            SENSOR_TYPE_DATA_REMAINING,
            "Data Remaining",
            "mdi:download-outline",
            DATA_GIGABYTES,
            SensorStateClass.MEASUREMENT,
        ),
        SuperloopSensor(
            coordinator,
            SENSOR_TYPE_DATA_LIMIT,
            "Data Limit",
            "mdi:download-network",
            DATA_GIGABYTES,
            SensorStateClass.TOTAL,
        ),
        SuperloopSensor(
            coordinator,
            SENSOR_TYPE_DAYS_REMAINING,
            "Days Remaining",
            "mdi:calendar-clock",
            "days",
            SensorStateClass.MEASUREMENT,
        ),
        SuperloopSensor(
            coordinator,
            SENSOR_TYPE_PLAN_SPEED,
            "Plan Speed",
            "mdi:speedometer",
            DATA_MEGABITS_PER_SECOND,
            SensorStateClass.MEASUREMENT,
        ),
        SuperloopSensor(
            coordinator,
            SENSOR_TYPE_BILLING_CYCLE_START,
            "Billing Cycle Start",
            "mdi:calendar-start",
            None,
            None,
            SensorDeviceClass.DATE,
        ),
        SuperloopSensor(
            coordinator,
            SENSOR_TYPE_BILLING_CYCLE_END,
            "Billing Cycle End",
            "mdi:calendar-end",
            None,
            None,
            SensorDeviceClass.DATE,
        ),
    ]

    async_add_entities(entities)


class SuperloopSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Superloop sensor."""

    def __init__(
        self,
        coordinator: SuperloopDataUpdateCoordinator,
        sensor_type: str,
        name: str,
        icon: str,
        unit_of_measurement: Optional[str] = None,
        state_class: Optional[str] = None,
        device_class: Optional[str] = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_state_class = state_class
        self._attr_device_class = device_class
        self._attr_unique_id = f"{DOMAIN}_{sensor_type}"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data or "services" not in self.coordinator.data or not self.coordinator.data["services"]:
            return None
            
        service = self.coordinator.data["services"][0]  # Assuming first service
        
        if self._sensor_type == SENSOR_TYPE_DATA_USED:
            # Extract used data from the service response
            if "usage" in service and "totalUsedMB" in service["usage"]:
                # Convert MB to GB
                return round(service["usage"]["totalUsedMB"] / 1024, 2)
            return None
            
        elif self._sensor_type == SENSOR_TYPE_DATA_REMAINING:
            # Calculate remaining data
            if "usage" in service and "totalUsedMB" in service["usage"] and "includedQuotaMB" in service["usage"]:
                used_mb = service["usage"]["totalUsedMB"]
                total_mb = service["usage"]["includedQuotaMB"]
                remaining_mb = max(0, total_mb - used_mb)
                return round(remaining_mb / 1024, 2)
            return None
            
        elif self._sensor_type == SENSOR_TYPE_DATA_LIMIT:
            # Extract data limit
            if "usage" in service and "includedQuotaMB" in service["usage"]:
                return round(service["usage"]["includedQuotaMB"] / 1024, 2)
            return None
            
        elif self._sensor_type == SENSOR_TYPE_DAYS_REMAINING:
            # Calculate days remaining in billing cycle
            if "billingDetails" in service and "cycleEndDate" in service["billingDetails"]:
                try:
                    end_date = datetime.strptime(service["billingDetails"]["cycleEndDate"], "%Y-%m-%d")
                    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    days_remaining = (end_date - today).days
                    return max(0, days_remaining)
                except (ValueError, TypeError):
                    return None
            return None
            
        elif self._sensor_type == SENSOR_TYPE_PLAN_SPEED:
            # Extract plan speed
            if "serviceDetails" in service and "downloadSpeedMbps" in service["serviceDetails"]:
                return service["serviceDetails"]["downloadSpeedMbps"]
            return None
            
        elif self._sensor_type == SENSOR_TYPE_BILLING_CYCLE_START:
            # Extract billing cycle start date
            if "billingDetails" in service and "cycleStartDate" in service["billingDetails"]:
                try:
                    return service["billingDetails"]["cycleStartDate"]
                except (ValueError, TypeError):
                    return None
            return None
            
        elif self._sensor_type == SENSOR_TYPE_BILLING_CYCLE_END:
            # Extract billing cycle end date
            if "billingDetails" in service and "cycleEndDate" in service["billingDetails"]:
                try:
                    return service["billingDetails"]["cycleEndDate"]
                except (ValueError, TypeError):
                    return None
            return None
            
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional information about the sensor."""
        if not self.coordinator.data or "services" not in self.coordinator.data or not self.coordinator.data["services"]:
            return {}
            
        service = self.coordinator.data["services"][0]
        
        attributes = {}
        
        # Add relevant attributes based on the sensor type
        if self._sensor_type in [SENSOR_TYPE_DATA_USED, SENSOR_TYPE_DATA_REMAINING, SENSOR_TYPE_DATA_LIMIT]:
            if "usage" in service:
                attributes["last_updated"] = service["usage"].get("lastUpdated")
                
        if "serviceDetails" in service:
            attributes["service_id"] = service["serviceDetails"].get("serviceId")
            attributes["service_type"] = service["serviceDetails"].get("serviceType")
            
        if "billingDetails" in service:
            attributes["plan_name"] = service["billingDetails"].get("planName")
            
        return attributes