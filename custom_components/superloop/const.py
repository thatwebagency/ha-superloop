"""Constants for the Superloop integration."""

DOMAIN = "superloop"
PLATFORMS = ["sensor"]

# API
API_BASE_URL = "https://webservices.myexetel.exetel.com.au/api"
API_LOGIN_ENDPOINT = "/login"
API_GET_SERVICES_ENDPOINT = "/getServices"

# Data update interval in seconds (15 minutes)
UPDATE_INTERVAL = 15 * 60

# Config
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_CUSTOMER_ID = "customer_id"

# Sensor types
SENSOR_TYPE_DATA_USED = "data_used"
SENSOR_TYPE_DATA_REMAINING = "data_remaining"
SENSOR_TYPE_DATA_LIMIT = "data_limit"
SENSOR_TYPE_DAYS_REMAINING = "days_remaining"
SENSOR_TYPE_PLAN_SPEED = "plan_speed"
SENSOR_TYPE_BILLING_CYCLE_START = "billing_cycle_start"
SENSOR_TYPE_BILLING_CYCLE_END = "billing_cycle_end"

# Units of measurement
DATA_GIGABYTES = "GB"
DATA_MEGABITS_PER_SECOND = "Mbps"