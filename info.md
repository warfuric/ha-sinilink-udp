# Sinilink XY-WFTX (Local UDP)

**Read-only** local monitoring of the Sinilink XY-WFTX WiFi thermostat. No cloud, no firmware flashing.

Polls the device over UDP/1024 (the `SINILINK521` discovery protocol) and surfaces:

- `climate` — current temperature, hysteresis start/stop band, heating/idle/off state (idle while e-stop is active)
- `sensor.temperature` — current measured temperature
- `binary_sensor.e_stop` — device e-stop flag (`problem` device class)
- `binary_sensor.led` — LED state
- `binary_sensor.temperature_alarm` — derived from the device's own high/low buzzer thresholds; fires only when the matching alarm is armed

**Not** writable — the XY-WFTX firmware tested does not accept control commands over UDP/1024. The official Sinilink app drives the device via the cloud MQTT broker. For write control you need to either stand up a local MQTT broker (DNS redirect) or flash ESPHome onto the ESP8285.

## Setup

1. Install via HACS, restart Home Assistant.
2. **Settings → Devices & Services → + Add Integration → "Sinilink XY-WFTX"**.
3. Either let it broadcast-scan the LAN or enter the device's IP and MAC manually.
