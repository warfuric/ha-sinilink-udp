# Sinilink XY-WFTX

Local monitoring and control of the Sinilink XY-WFTX WiFi thermostat. No cloud, no firmware flashing.

**Read path (always available):** Polls the device via UDP/1024 every 10s.

**Write path (requires local MQTT broker):** Publishes commands via MQTT by intercepting the device's cloud connection with a local Mosquitto broker and DNS override.

Entities:
- `climate` -- hysteresis thermostat with start/stop temp range, HVAC heat/off
- `sensor.temperature` -- current measured temperature
- `switch.relay`, `switch.led`, `switch.e_stop`, `switch.notifications` -- writable controls (MQTT required)
- `binary_sensor.e_stop`, `binary_sensor.temperature_alarm` -- problem alerts

## Setup

1. Install via HACS, restart Home Assistant.
2. **Settings -> Devices & Services -> + Add Integration -> "Sinilink XY-WFTX"**.
3. Scan the LAN or enter device IP/MAC manually.
4. Optionally configure a local MQTT broker for write control.

## MQTT broker setup (for write control)

1. Run Mosquitto on your LAN with `listener 1884` and `allow_anonymous true`.
2. DNS override `mq.sinilink.com` to the broker's IP (Pi-hole / router).
3. Power-cycle the device.
4. Enter the broker address in the integration's MQTT configuration step.
