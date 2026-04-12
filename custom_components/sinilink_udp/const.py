"""Constants for the Sinilink XY-WFTX integration."""
from __future__ import annotations

DOMAIN = "sinilink_udp"

# UDP status endpoint (read-only).
UDP_PORT = 1024
DISCOVERY_PAYLOAD = b"SINILINK521"
BROADCAST_ADDR = "255.255.255.255"

DEFAULT_POLL_INTERVAL = 10  # seconds
UDP_TIMEOUT = 3.0           # seconds
DISCOVERY_DURATION = 3.0    # seconds to listen for broadcast replies

MANUFACTURER = "Sinilink"
MODEL = "XY-WFTX"

# MQTT broker config (for write control via local broker interception).
CONF_MQTT_HOST = "mqtt_host"
CONF_MQTT_PORT = "mqtt_port"
DEFAULT_MQTT_PORT = 1884

# MQTT topic prefixes. All topics are suffixed with the device MAC.
MQTT_TOPIC_STATUS = "PROWT"           # device publishes status every ~30s
MQTT_TOPIC_COMMAND = "APPWT"          # publish commands here
MQTT_TOPIC_ONLINE = "returnisonline"  # retained online/offline

# MQTT command method names.
# Commands are JSON: {"method":"<name>","param":<value>,"time":<epoch>}
# Note: param types vary — some are strings ("open", "1"), others numbers.
MQTT_CMD_RELAY = "relay"          # "open" / "close"
MQTT_CMD_MODE = "oprate"          # "A" / "M"
MQTT_CMD_START_TEMP = "stemp"     # number
MQTT_CMD_STOP_TEMP = "btemp"      # number
MQTT_CMD_ALARM_HIGH = "otp"       # number
MQTT_CMD_ALARM_LOW = "ltp"        # number
MQTT_CMD_ESTOP = "stop"           # 1 / 0
MQTT_CMD_DELAY_ENABLE = "sw_dly"  # 1 / 0
MQTT_CMD_DELAY_VALUE = "delay"    # number (seconds)
MQTT_CMD_NOTIFICATIONS = "wechat" # "1" / "0"
MQTT_CMD_LED = "led"              # "1" / "0"
MQTT_CMD_UNIT = "unit"            # "C" / "F"

# Indices into the device's `param` array. Verified against the official
# Sinilink app (April 2026) and confirmed via MQTT command capture.
PARAM_RELAY = 0          # 1 = on, 0 = off
PARAM_MODE = 1           # "A" auto, "M" manual
PARAM_CURRENT_TEMP = 3   # measured temperature
PARAM_UNIT = 4           # "C" or "F"
PARAM_HEAT_COOL = 5      # "H" heat, "C" cool
PARAM_START_TEMP = 6     # heater ON below this
PARAM_STOP_TEMP = 7      # heater OFF above this
PARAM_DELAY_VALUE = 9    # delay timer (seconds)
PARAM_ALARM_HIGH_ENABLE = 10  # 1 = high-temp alarm armed
PARAM_ALARM_HIGH = 11         # high buzzer alarm threshold
PARAM_ALARM_LOW_ENABLE = 12   # 1 = low-temp alarm armed
PARAM_ALARM_LOW = 13          # low buzzer alarm threshold
PARAM_POWER_ON_STATE = 17  # 1 = remember last state on power-on (always 1 in captures)
PARAM_ESTOP = 18           # 1 = e-stop armed, 0 = disengaged
PARAM_DELAY_ENABLE = 19    # 1 = delay timer active
PARAM_NOTIFICATIONS = 20 # 1 = cloud push notifications enabled
PARAM_LED = 21           # 1 = LED on, 0 = off
# Read-only modbus configuration:
PARAM_MODBUS_BAUD = 22   # 115200
PARAM_MODBUS_SLAVE = 23  # 1
