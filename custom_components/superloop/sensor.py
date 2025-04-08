from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
