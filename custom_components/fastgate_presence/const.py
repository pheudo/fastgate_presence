"""Constants for FASTGate Presence integration."""

DOMAIN = "fastgate_presence"

# Options keys (user preferences, stored in entry.options)
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MONITORED_DEVICES = "monitored_devices"
CONF_DEVICE_NAMES = "device_names"

# Defaults
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

# Device registry metadata
MANUFACTURER = "Huawei"
MODEL = "Router Client"
ROUTER_MODEL = "FASTGate DN8245F2"

# Extra state attribute keys
ATTR_MAC = "mac_address"
ATTR_IP = "ip_address"
ATTR_HOSTNAME = "hostname"
ATTR_NETWORK_TYPE = "network_type"

NETWORK_TYPE_WIFI = "WiFi"
NETWORK_TYPE_LAN = "LAN"
