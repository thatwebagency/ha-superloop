"""Sensor platform for Superloop integration."""
from __future__ import annotations

import logging
import re
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
    SENSOR_TYPE_EVENING_SPEED,
)
from .coordinator import SuperloopDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Superloop sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Check that we have valid data
    if not coordinator.data:
        _LOGGER.error("No data received from Superloop API")
        return
        
    # The response format is different than originally expected
    # It has broadband, mobile, and phone as top-level keys
    if not coordinator.data.get("broadband"):
        _LOGGER.error("No broadband services found in Superloop data")
        return
        
    # Use the first broadband service
    service = coordinator.data["broadband"][0]
    
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
            SENSOR_TYPE_EVENING_SPEED,
            "Evening Speed",
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
        if not self.coordinator.data or not self.coordinator.data.get("broadband"):
            return None
            
        service = self.coordinator.data["broadband"][0]  # Using first broadband service
        
        if self._sensor_type == SENSOR_TYPE_DATA_USED:
            # Extract used data from usage summary
            if "usageSummary" in service and "totalBytes" in service["usageSummary"]:
                # Convert bytes to GB
                return round(service["usageSummary"]["totalBytes"] / 1024 / 1024 / 1024, 2)
            elif "usageSummary" in service and "total" in service["usageSummary"]:
                # Parse from the total string (e.g., "323.27GB")
                try:
                    data_str = service["usageSummary"]["total"]
                    data_value = float(re.search(r'([\d.]+)', data_str).group(1))
                    return data_value
                except (AttributeError, ValueError):
                    return None
            return None
            
        elif self._sensor_type == SENSOR_TYPE_DATA_REMAINING:
            # For unlimited plans, there's no data remaining to calculate
            if "isUnlimitedUsage" in service and service["isUnlimitedUsage"]:
                return float('inf')  # Infinity for unlimited
                
            # If there's a usage summary with data limit, calculate remaining
            if "usageSummary" in service:
                # Check if the summaryText has the format like "323.27GB/Unlimited" or "50GB/100GB"
                summary = service["usageSummary"].get("summaryText", "")
                if "/" in summary:
                    parts = summary.split("/")
                    if "nlimited" in parts[1]:  # Match "Unlimited" case-insensitive
                        return float('inf')  # Infinity for unlimited
                    
                    try:
                        used_str = parts[0]
                        limit_str = parts[1]
                        
                        used_value = float(re.search(r'([\d.]+)', used_str).group(1))
                        limit_value = float(re.search(r'([\d.]+)', limit_str).group(1))
                        
                        return round(limit_value - used_value, 2)
                    except (AttributeError, ValueError, IndexError):
                        return None
            return None
            
        elif self._sensor_type == SENSOR_TYPE_DATA_LIMIT:
            # For unlimited plans, return a very large number
            if "isUnlimitedUsage" in service and service["isUnlimitedUsage"]:
                return float('inf')  # Infinity for unlimited
                
            # If there's a usage summary with data limit in the summaryText
            if "usageSummary" in service:
                summary = service["usageSummary"].get("summaryText", "")
                if "/" in summary:
                    limit_part = summary.split("/")[1]
                    if "nlimited" in limit_part:  # Match "Unlimited" case-insensitive
                        return float('inf')  # Infinity for unlimited
                    
                    try:
                        limit_value = float(re.search(r'([\d.]+)', limit_part).group(1))
                        return limit_value
                    except (AttributeError, ValueError):
                        return None
                        
            # Check if allowance field contains the data limit
            if "allowance" in service:
                allowance = service["allowance"]
                if "nlimited" in allowance:  # Match "Unlimited" case-insensitive
                    return float('inf')  # Infinity for unlimited
                    
                try:
                    limit_value = float(re.search(r'([\d.]+)', allowance).group(1))
                    return limit_value
                except (AttributeError, ValueError):
                    return None
            return None
            
        elif self._sensor_type == SENSOR_TYPE_DAYS_REMAINING:
            # Extract from daysLeftInCurrentBillingCycleText 
            if "daysLeftInCurrentBillingCycleText" in service:
                days_text = service["daysLeftInCurrentBillingCycleText"]
                try:
                    days = int(re.search(r'(\d+)', days_text).group(1))
                    return days
                except (AttributeError, ValueError):
                    return None
            return None
            
        elif self._sensor_type == SENSOR_TYPE_PLAN_SPEED:
            # Extract from speed field (format like "1000/50")
            if "speed" in service:
                speed_text = service["speed"]
                try:
                    download_speed = int(speed_text.split("/")[0])
                    return download_speed
                except (ValueError, IndexError):
                    return None
            return None
            
        elif self._sensor_type == SENSOR_TYPE_EVENING_SPEED:
            # Extract from eveningSpeed field (format like "811 Mbps")
            if "eveningSpeed" in service:
                speed_text = service["eveningSpeed"]
                try:
                    evening_speed = int(re.search(r'(\d+)', speed_text).group(1))
                    return evening_speed
                except (AttributeError, ValueError):
                    return None
            return None
            
        elif self._sensor_type == SENSOR_TYPE_BILLING_CYCLE_START:
            # For the next billing cycle start date
            if "nextBillingCycleStart" in service:
                date_text = service["nextBillingCycleStart"]
                try:
                    # Convert "27 Apr 25" format to YYYY-MM-DD
                    date_obj = datetime.strptime(date_text, "%d %b %y")
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    return date_text  # Return as-is if parsing fails
            return None
            
        elif self._sensor_type == SENSOR_TYPE_BILLING_CYCLE_END:
            # For the current billing cycle end date
            if "currentBillingCycleEnd" in service:
                date_text = service["currentBillingCycleEnd"]
                try:
                    # Convert "26 Apr 25" format to YYYY-MM-DD
                    date_obj = datetime.strptime(date_text, "%d %b %y")
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    return date_text  # Return as-is if parsing fails
            return None
            
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional information about the sensor."""
        if not self.coordinator.data or not self.coordinator.data.get("broadband"):
            return {}
            
        service = self.coordinator.data["broadband"][0]
        
        attributes = {}
        
        # Add common attributes for all sensors
        attributes["service_number"] = service.get("serviceNumber")
        attributes["address"] = service.get("address")
        attributes["plan_title"] = service.get("planTitle")
        attributes["plan_heading"] = service.get("planHeading")
        attributes["monthly_charge"] = service.get("monthlyCharge")
        
        # Add specific attributes based on sensor type
        if self._sensor_type in [SENSOR_TYPE_DATA_USED, SENSOR_TYPE_DATA_REMAINING, SENSOR_TYPE_DATA_LIMIT]:
            if "usageSummary" in service:
                attributes["summary_text"] = service["usageSummary"].get("summaryText")
                attributes["unlimited"] = service.get("isUnlimitedUsage", False)
                
        if self._sensor_type in [SENSOR_TYPE_PLAN_SPEED, SENSOR_TYPE_EVENING_SPEED]:
            attributes["speed"] = service.get("speed")
            attributes["evening_speed"] = service.get("eveningSpeed")
            attributes["plan_speed"] = service.get("planSpeed")
            
        if self._sensor_type in [SENSOR_TYPE_BILLING_CYCLE_START, SENSOR_TYPE_BILLING_CYCLE_END, SENSOR_TYPE_DAYS_REMAINING]:
            attributes["billing_cycle_progress"] = service.get("billingCycleProgressPercentage")
            attributes["current_billing_cycle_end"] = service.get("currentBillingCycleEnd")
            attributes["next_billing_cycle_start"] = service.get("nextBillingCycleStart")
            
        return attributes