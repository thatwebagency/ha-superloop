"""Constants for the Superloop integration."""

DOMAIN = "superloop"
PLATFORMS = ["sensor"]

# === API Base URLs ===
API_BASE_URL = "https://webservices.myexetel.exetel.com.au/api"
API_LEGACY_AUTH_TOKEN_ENDPOINT = "/auth/token"          # Legacy login + 2FA
API_LEGACY_REFRESH_TOKEN_ENDPOINT = "/auth/token/refresh"
API_LEGACY_VERIFY_2FA_ENDPOINT = "/auth/verify2fa"

# New long-lived JWT login (no 2FA, 1 year expiry)
API_JWT_LOGIN_URL = "https://webservices-api.superloop.com/v1/login-jwt"

# Services / Usage
API_GET_SERVICES_ENDPOINT = "/getServices"
API_GET_DAILY_USAGE_ENDPOINT = "/getBroadbandDailyUsage"  # append /{service_id}

# Authentication Constants
AUTH_BRAND = "superloop"
AUTH_PERSIST_LOGIN = True  # safer default with JWT login

# Config Entry Keys
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"     # only present for legacy auth
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_EXPIRES_IN = "expires_in"
CONF_EXPIRES_AT_MS = "expires_at_ms"
CONF_LOGIN_METHOD = "login_method"       # "login_jwt" or "legacy_auth"

# Authentication Error Messages
AUTH_ERROR_INVALID_CREDENTIALS = "Invalid username or password"
AUTH_ERROR_GENERIC = "Authentication failed"

# Data update interval in seconds (15 minutes)
UPDATE_INTERVAL = 15 * 60

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
