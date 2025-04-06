"""Constants for the Superloop integration."""

DOMAIN = "superloop"
PLATFORMS = ["sensor"]

# API
API_BASE_URL = "https://webservices.myexetel.exetel.com.au/api"
API_GET_SERVICES_ENDPOINT = "/getServices"

# OAuth Config
SUPERLOOP_LOGIN_URL = "https://superhub.superloop.com/login"
AUTH_CALLBACK_PATH = "/api/superloop/auth"
AUTH_CALLBACK_NAME = "superloop_auth_view_registered"

# Config Entry Keys
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"

# Data update interval in seconds (15 minutes)
UPDATE_INTERVAL = 15 * 60

# Config
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"

# Sensor types
SENSOR_TYPE_DATA_USED = "data_used"
SENSOR_TYPE_DATA_REMAINING = "data_remaining"
SENSOR_TYPE_DATA_LIMIT = "data_limit"
SENSOR_TYPE_DAYS_REMAINING = "days_remaining"
SENSOR_TYPE_PLAN_SPEED = "plan_speed"
SENSOR_TYPE_BILLING_CYCLE_START = "billing_cycle_start"
SENSOR_TYPE_BILLING_CYCLE_END = "billing_cycle_end"
SENSOR_TYPE_EVENING_SPEED = "evening_speed"

# Units of measurement
DATA_GIGABYTES = "GB"
DATA_MEGABITS_PER_SECOND = "Mbps"