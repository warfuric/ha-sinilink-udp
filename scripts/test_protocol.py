#!/usr/bin/env python3
"""Offline smoke test for protocol.parse_status / build_command.

Run from the repo root:

    python3 scripts/test_protocol.py

This does NOT touch a real device. It feeds a captured-style reply through
the parser and round-trips a command. Replace SAMPLE_REPLY with a real
capture once you have one (see README.md for the discovery one-liner).
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

# Real reply captured from a Sinilink XY-WFTX (78:42:1C:E4:7D:5C).
# Note: this firmware sends pure JSON (no MAC, prefix) and uses "tim"
# instead of "time". current_temp is at index 3, target min/max at 6/7.
SAMPLE_REPLY = (
    b'{"MAC":"78:42:1C:E4:7D:5C",'
    b'"param":[0,"A",0,22.2,"C","H",58,65,0,0,1,70,1,10,1,0,5,1,1,0,1,0,115200,1,20482,112],'
    b'"ERR":0,"tim":1775466949}'
)


def main() -> int:
    status = protocol.parse_status(SAMPLE_REPLY)
    print("parsed:", json.dumps(status.as_dict(), indent=2))

    assert status.mac == "78:42:1C:E4:7D:5C", status.mac
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
    assert status.estop is True  # this capture was taken with e-stop active
    assert status.led is False           # LED off (param[21]=0)
    assert status.notifications is True  # notifications on (param[20]=1)

    # Round-trip a control command: bump stop temp to 68.
    new_param = list(status.param)
    new_param[7] = 68
    cmd = protocol.build_command(status.mac, new_param, epoch=1775466950)
    print("command bytes:", cmd)
    assert cmd.startswith(b"78:42:1C:E4:7D:5C{")
    assert b'"param":[0,"A",0,22.2,"C","H",58,68' in cmd

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
