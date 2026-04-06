# Sinilink XY-WFTX (Local UDP) — Home Assistant integration

**Read-only** local monitoring of the Sinilink XY-WFTX WiFi thermostat over its UDP/1024 status endpoint. No cloud, no firmware flashing.

## Reference hardware

This integration was built and verified against the **D3D Store "Chamber Heater for Bambu Lab P1S / X1C / P1P"** kit on AliExpress:

**[Chamber Heater for Bambu Lab P1S / X1C / P1P — D3D Store](https://www.aliexpress.com/item/1005007451846333.html)**

The kit bundles a PTC heating element with the Sinilink XY-WFTX WiFi thermostat controller (ESP8285, 10A relay, NTC + DS18B20 inputs). "Sinilink" doesn't appear in the AliExpress listing title — the WiFi controller is just the brains of the bundled chamber heater kit. Other kits on AliExpress that use the same Sinilink XY-WFTX module (any listing showing a small black box with a red 7-segment display, WiFi, and a blue buzzer — often branded "XY-WFT1" or "XY-WFTX") should also work, but **only the D3D Store kit has been verified.**

> ⚠️ **Read-only.** The XY-WFTX firmware (verified against a unit with MAC `78:42:1C:E4:7D:5C`) does **not** accept control commands over UDP/1024. The endpoint is status-only — writes are silently ignored. The official Sinilink app drives the device via the cloud MQTT broker `ws://mq.sinilink.com:8085/mqtt`, not via local UDP. CVE-2022-43704's "unauthenticated UDP control" was likely a different firmware revision. See "Future work" below for paths to control.

## What you get (v0.1)

- `climate.sinilink_<MAC>_thermostat` — read-only display: current temp, start/stop band, hvac action (heating/idle/off, with idle while e-stop is active)
- `sensor.sinilink_<MAC>_temperature` — current measured temperature
- `binary_sensor.sinilink_<MAC>_e_stop` — `problem` device class, on while the device's e-stop is tripped
- Config flow with broadcast discovery (`SINILINK521`) and manual IP/MAC fallback
- Polls the device every 10s; reflects changes made from the physical buttons or the official Sinilink app

This is enough to build HA automations on (alert if e-stop trips, alert if chamber temp drifts outside a window, log the chamber temperature for print correlation, etc.) — you just can't *command* the heater from HA.

In HA's "set target temperature" dialog you'll see two sliders: the **low**
slider is the device's *start temp* (heater turns on below this), the
**high** slider is the *stop temp* (heater turns off above this). The
device's separate buzzer-alarm thresholds are surfaced as state attributes
(`alarm_high`, `alarm_low`) but aren't writable from the climate entity.

## Install

### Option 1 — HACS (recommended)

1. HACS → **Integrations** → top-right menu → **Custom repositories**.
2. Add `https://github.com/warfuric/ha-sinilink-udp` as category **Integration**.
3. Install **Sinilink XY-WFTX (Local UDP)**, restart Home Assistant.

### Option 2 — Samba (HAOS)

1. Enable the **Samba share** addon.
2. Mount `\\<HA-IP>\config` from your OS (e.g. `smb://homeassistant.local`).
3. Copy `custom_components/sinilink_udp/` into `config/custom_components/`.
4. **Settings → System → Restart**.

### Option 3 — SSH (dev / CI)

```bash
cp .env.example .env   # first time only — fill in HA_HOST
./scripts/deploy.sh
```

Requires the **Advanced SSH & Web Terminal** addon (Protection mode OFF so `ha core restart` works). See `.env.example` for all configuration variables.

## Add the device

Settings → Devices & Services → **Add Integration** → "Sinilink XY-WFTX (Local UDP)"

- "Scan network" — broadcasts `SINILINK521` to `255.255.255.255:1024` and lists replies.
- "Enter manually" — type the device's IP and MAC; we validate by sending a single discovery packet.

## Verifying the device speaks the protocol

Before installing, confirm the device replies to discovery from a machine on the same LAN:

```bash
python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(3); s.sendto(b'SINILINK521', ('DEVICE_IP_HERE', 1024)); print(s.recv(2048))"
```

You should see something like:

```
b'4C:EB:D6:01:A8:7C,{"MAC":"4C:EB:D6:01:A8:7C","time":...,"param":[1,"M",0,20.8,"C","H",66,5,0,0,0,20.5,...]}'
```

If `param` indices differ from the table below for your firmware, adjust `custom_components/sinilink_udp/const.py`.

| Index | App label | Meaning |
|------:|---|---|
| 0 | Relay | 1 = heating, 0 = off |
| 1 | Mode | "A" auto (hysteresis), "M" manual |
| 3 | Current temp | Measured temperature |
| 4 | Unit | "C" / "F" |
| 5 | — | "H" heat / "C" cool |
| 6 | **Start temp** | Heater turns ON below this |
| 7 | **Stop temp** | Heater turns OFF above this |
| 11 | **High threshold** | Buzzer alarm above this (not a cutoff) |
| 13 | **Low threshold** | Buzzer alarm below this |
| 18 | **E-stop** | 1 = e-stop tripped, heater inhibited; 0 = normal |

The integration only drives **Auto** mode — it'll force `mode = "A"` on
every write, since manual mode bypasses the start/stop band that HA shows
the user. The device's timer/cycle features and Manual mode are not
exposed.

> Note: the original reverse-engineering guide used a different firmware
> revision. This integration's map was verified against the official
> Sinilink app on a real device (replies use `"tim"` instead of `"time"`
> and have no leading `MAC,` prefix). If your device shows different
> values, edit `const.py`.

## Roadmap

**v0.1 (current) — read-only monitoring.** Everything the device exposes on UDP/1024, surfaced as HA entities.

### v0.2 — Capture the MQTT control protocol

Goal: understand exactly what the official Sinilink app sends the device so we can replay it. The app uses the cloud broker `ws://mq.sinilink.com:8085/mqtt`, which is unauthenticated (CVE-2022-43704), so we can stand our own broker in front of it without needing to crack anything.

Approach (a.k.a. **local cloud interception** / DNS override / split-horizon DNS):

1. Stand up a local Mosquitto on the LAN with a WebSocket listener on port 8085 (`listener 8085`, `protocol websockets`, `allow_anonymous true`).
2. Add a DNS override on your router or Pi-hole so `mq.sinilink.com` resolves to the local broker's IP.
3. Power-cycle the device so it re-resolves and connects to your broker.
4. Subscribe to `#` on the local broker and log everything:
   ```bash
   mosquitto_sub -h localhost -p 8085 -t '#' -v > sinilink-traffic.log
   ```
5. Drive every control from the official app (start/stop temps, mode, LED, alarms, e-stop clear) and diff the published topics to build a full command table.
6. Capture both the "hello" / subscription topics (what the device expects *from* the broker) and the status topics (what it publishes), so we know which messages to craft in the opposite direction.

Deliverable: a document mapping every app action to its MQTT topic + payload shape.

### v0.3 — Write support via the local MQTT path

Once the command set is known, extend the integration to optionally connect to a local MQTT broker (reusing HA's existing MQTT integration or a dedicated client) and publish control messages to the topics the device already subscribes to. Climate entity becomes writable again:

- `async_set_temperature` → publish new start/stop band
- `async_set_hvac_mode(OFF)` → publish a manual-off / e-stop-engage payload
- New `switch.led`, `switch.buzzer_alarms`, `switch.notifications` for the toggleables
- Optional `button.clear_estop` service

The config flow grows a second step asking for the MQTT broker address (defaulting to HA's own broker if configured) and whether the DNS redirect is in place. UDP polling stays as the authoritative *read* path — MQTT is only used for writes.

### v0.4 — Full feature parity

- Timer / cycle features (indices `[2, 8, 9, 14, 15, 16, 17, 19]` — currently unmapped; correlate against the app's timer screen)
- Temperature offset / calibration (if the device exposes one)
- Power-on state preference
- Custom Lovelace card with a 7-segment font and a big red e-stop button (originally proposed in the reverse-engineering guide)

### Alternative path — flash ESPHome

If the MQTT interception turns out to be fragile (firmware changes, broken TLS pinning in a future update, …), the nuclear option is to flash ESPHome onto the ESP8285. Requires:

- 1.27 mm pitch header access (soldering or test clips)
- USB-UART adapter, 3.3V only
- **DOUT flash mode** (critical — DIO/QIO will brick the ESP8285)
- YAML config with `platform: ESP8266`, `board: esp8285`, GPIO pinout per the XY-WFT1 Tasmota template (relay GPIO5, NTC on ADC0, button GPIO14, LED GPIO12, buzzer GPIO2)

This bypasses the Sinilink firmware entirely, gives native HA API integration, and removes any cloud dependency — at the cost of hardware work and a backup-then-hope flash operation. See section 4 of the reverse-engineering doc for the full procedure.

### Out of scope (probably forever)

- Re-enabling UDP/1024 writes. The firmware on the tested unit simply does not have a write handler on that port — no amount of payload tweaking will change that.
- Supporting the old Sinilink cloud app long-term. The whole point of this integration is to stop depending on `mq.sinilink.com`.

## Acknowledgements

- **[9lyph/CVE-2022-43704](https://github.com/9lyph/CVE-2022-43704)** — original security research disclosing the unauthenticated UDP/1024 endpoint and the `SINILINK521` discovery magic string. This integration started from their proof-of-concept; the parser in `protocol.py` is structurally inspired by their PoC, adapted and extended after the `param` array layout turned out to differ from the firmware they tested.
- **[Tasmota XY-WFT1 template](https://templates.blakadder.com/sinilink_XY-WFT1.html)** and the Tasmota/ESPHome communities for the GPIO pinout reference used in the ESPHome path discussed in the roadmap.
