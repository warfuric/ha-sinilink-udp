#!/usr/bin/env python3
"""Offline smoke test for protocol.parse_status / build_command / build_mqtt_command.

Run from the repo root:

    python3 scripts/test_protocol.py

This does NOT touch a real device. It feeds a sample reply through the
parser and round-trips commands.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

# Load protocol.py and const.py without going through the package __init__
# (which imports Home Assistant). We register a tiny synthetic package so the
# `from .const import ...` relative import in protocol.py resolves.
REPO_ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = REPO_ROOT / "custom_components" / "sinilink_udp"

pkg = types.ModuleType("sinilink_udp_test")
pkg.__path__ = [str(PKG_DIR)]
sys.modules["sinilink_udp_test"] = pkg


def _load(name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"sinilink_udp_test.{name}", PKG_DIR / f"{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"sinilink_udp_test.{name}"] = module
    spec.loader.exec_module(module)
    return module


_load("const")
protocol = _load("protocol")

# Sample reply matching the XY-WFTX firmware format.
# Pure JSON (no MAC prefix), uses "tim" not "time".
TEST_MAC = "AA:BB:CC:DD:EE:FF"
SAMPLE_REPLY = (
    b'{"MAC":"AA:BB:CC:DD:EE:FF",'
    b'"param":[0,"A",0,22.2,"C","H",58,65,0,0,1,70,1,10,1,0,5,1,1,0,1,0,115200,1,20482,112],'
    b'"ERR":0,"tim":1775466949}'
)


def main() -> int:
    # --- Parse status ---
    status = protocol.parse_status(SAMPLE_REPLY)
    print("parsed:", json.dumps(status.as_dict(), indent=2))

    assert status.mac == TEST_MAC, status.mac
    assert status.epoch == 1775466949
    assert status.relay is False
    assert status.mode == "A"
    assert status.current_temp == 22.2
    assert status.unit == "C"
    assert status.heat_cool == "H"
    assert status.start_temp == 58
    assert status.stop_temp == 65
    assert status.alarm_high == 70
    assert status.alarm_high_enabled is True
    assert status.alarm_low == 10
    assert status.alarm_low_enabled is True
    assert status.estop is True   # param[17]=1
    assert status.delay_value == 0
    assert status.delay_enabled is False
    assert status.led is False
    assert status.notifications is True

    # --- UDP command round-trip ---
    new_param = list(status.param)
    new_param[7] = 68
    cmd = protocol.build_command(TEST_MAC, new_param, epoch=1775466950)
    print("UDP command:", cmd)
    assert cmd.startswith(f"{TEST_MAC}{{".encode())
    assert b'"param":[0,"A",0,22.2,"C","H",58,68' in cmd

    # --- MQTT command ---
    mqtt_cmd = protocol.build_mqtt_command("btemp", 68, epoch=1775466950)
    print("MQTT command:", mqtt_cmd)
    parsed_cmd = json.loads(mqtt_cmd)
    assert parsed_cmd["method"] == "btemp"
    assert parsed_cmd["param"] == 68
    assert parsed_cmd["time"] == 1775466950

    # String param (relay)
    mqtt_relay = protocol.build_mqtt_command("relay", "open", epoch=1775466951)
    parsed_relay = json.loads(mqtt_relay)
    assert parsed_relay["method"] == "relay"
    assert parsed_relay["param"] == "open"

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
