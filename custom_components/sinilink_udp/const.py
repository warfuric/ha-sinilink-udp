"""Constants for the Sinilink XY-WFTX UDP integration."""
from __future__ import annotations

DOMAIN = "sinilink_udp"

UDP_PORT = 1024
DISCOVERY_PAYLOAD = b"SINILINK521"
BROADCAST_ADDR = "255.255.255.255"

DEFAULT_POLL_INTERVAL = 10  # seconds
UDP_TIMEOUT = 3.0           # seconds
DISCOVERY_DURATION = 3.0    # seconds to listen for broadcast replies

MANUFACTURER = "Sinilink"
MODEL = "XY-WFTX"

# Indices into the device's `param` array — verified against the app on a
# real XY-WFTX. The reverse-engineering guide's index map was for a
# different firmware revision and was wrong for this device.
#
# Terminology matches the official Sinilink app:
#   * "Start temp"  — heater relay turns ON below this (hysteresis low)
#   * "Stop temp"   — heater relay turns OFF above this (hysteresis high)
#   * "Threshold"   — buzzer alarm range (NOT a hard cutoff)
#   * Auto mode     — device cycles relay to hold the start/stop band
#   * Manual mode   — device runs the heater unconditionally (not exposed)
#
# The device also has an "E-stop" state shown in the app. We don't yet know
# which param index carries that flag; the raw `param` array is exposed as
# an entity attribute so it can be correlated against device state changes.
PARAM_RELAY = 0          # 1 = on, 0 = off
PARAM_MODE = 1           # "A" auto, "M" manual
PARAM_CURRENT_TEMP = 3   # measured temperature
PARAM_UNIT = 4           # "C" or "F"
PARAM_HEAT_COOL = 5      # "H" heat, "C" cool
PARAM_START_TEMP = 6     # heater ON below this
PARAM_STOP_TEMP = 7      # heater OFF above this
PARAM_ALARM_HIGH_ENABLE = 10  # 1 = high-temp alarm armed, 0 = disabled
PARAM_ALARM_HIGH = 11         # high buzzer alarm threshold
PARAM_ALARM_LOW_ENABLE = 12   # 1 = low-temp alarm armed, 0 = disabled
PARAM_ALARM_LOW = 13          # low buzzer alarm threshold
PARAM_ESTOP = 18         # 1 = e-stop tripped (heater inhibited), 0 = normal
PARAM_NOTIFICATIONS = 20 # 1 = cloud push notifications enabled
PARAM_LED = 21           # 1 = LED on, 0 = off (no visible effect on some units)
# Read-only modbus configuration (visible in app under "modbus"):
PARAM_MODBUS_BAUD = 22   # 115200
PARAM_MODBUS_SLAVE = 23  # 1
# Indices 24/25 (e.g. 20482, 112) are likely modbus product ID / device ID.

# IMPORTANT: This firmware does NOT accept control commands over UDP/1024.
# That endpoint is read-only. The official Sinilink app drives the device
# over its cloud MQTT channel (ws://mq.sinilink.com:8085/mqtt). UDP writes
# are silently ignored at best. This integration is therefore read-only.
# To get write control, see README "Future work" — the path is either to
# stand up a local MQTT broker that the device connects to (DNS redirect),
# or to flash ESPHome onto the ESP8285.
