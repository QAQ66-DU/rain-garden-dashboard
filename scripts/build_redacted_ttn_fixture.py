"""Build a small, deterministic, privacy-safe TTN console test fixture.

The source export remains a local ignored artifact. This script selects only the
few event shapes needed by automated tests, replaces external identifiers, and
adds one clearly documented invalid-decoding mutation for a negative test.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

FORWARD_EVENT_NAME = "as.up.data.forward"
SYNTHETIC_DEVICE_ID = "synthetic-outflow-a"
SYNTHETIC_APPLICATION_ID = "synthetic-rain-garden"


def _redact_scalar(key: str, value: Any) -> Any:
    replacements: dict[str, Any] = {
        "application_id": SYNTHETIC_APPLICATION_ID,
        "device_id": SYNTHETIC_DEVICE_ID,
        "dev_eui": "0000000000000000",
        "join_eui": "0000000000000000",
        "dev_addr": "00000000",
        "gateway_id": "synthetic-gateway",
        "eui": "0000000000000000",
        "session_key_id": "synthetic-session-key-id",
        "uplink_token": "synthetic-uplink-token",
        "tenant_id": "synthetic-tenant",
        "tenant-id": "synthetic-tenant",
        "user_id": "synthetic-user",
        "unique_id": "synthetic-console-event",
        "origin": "synthetic.example.invalid",
    }
    return replacements.get(key, value)


def _redact(value: Any, *, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            key: _redact(_redact_scalar(key, item), parent_key=key)
            for key, item in value.items()
        }
    if isinstance(value, list):
        if parent_key == "correlation_ids":
            return ["synthetic:correlation-id"]
        return [_redact(item, parent_key=parent_key) for item in value]
    return value


def _first_event(events: list[dict[str, Any]], name: str, *, has_status: bool) -> dict[str, Any]:
    for event in events:
        if event.get("name") != name:
            continue
        decoded = (
            event.get("data", {})
            .get("uplink_message", {})
            .get("decoded_payload", {})
        )
        messages = decoded.get("messages", [])
        flattened = [
            message
            for group in messages
            if isinstance(group, list)
            for message in group
            if isinstance(message, dict)
        ]
        contains_status = any(
            "Battery(%)" in message or "Firmware Version" in message
            for message in flattened
        )
        if contains_status == has_status:
            return event
    raise ValueError(f"No {name!r} event with has_status={has_status} was found")


def _first_non_uplink(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in events:
        if event.get("name") != FORWARD_EVENT_NAME:
            return event
    raise ValueError("No non-uplink event was found")


def build_fixture(events: list[dict[str, Any]]) -> dict[str, Any]:
    normal = _redact(_first_event(events, FORWARD_EVENT_NAME, has_status=False))
    status = _redact(_first_event(events, FORWARD_EVENT_NAME, has_status=True))
    invalid = copy.deepcopy(normal)
    invalid["unique_id"] = "synthetic-invalid-console-event"
    invalid["time"] = "2026-08-03T12:00:00Z"
    invalid["data"]["received_at"] = "2026-08-03T12:00:00Z"
    invalid["data"]["uplink_message"]["received_at"] = "2026-08-03T12:00:00Z"
    invalid["data"]["uplink_message"]["f_cnt"] = 999001
    invalid["data"]["uplink_message"]["decoded_payload"] = {
        "err": 1,
        "messages": [],
        "valid": False,
    }
    non_uplink = _redact(_first_non_uplink(events))

    return {
        "fixture_metadata": {
            "source": "privacy-redacted derivative of a local TTN Live Data console export",
            "synthetic_identifiers": True,
            "invalid_case": (
                "explicit test mutation because the source export contains no invalid "
                "as.up.data.forward event"
            ),
        },
        "events": [normal, status, invalid, non_uplink],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with args.source.open(encoding="utf-8") as source_file:
        source = json.load(source_file)
    if not isinstance(source, list) or not all(isinstance(item, dict) for item in source):
        raise ValueError("Expected a JSON array of TTN console event objects")

    fixture = build_fixture(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(fixture, output_file, indent=2, sort_keys=True)
        output_file.write("\n")


if __name__ == "__main__":
    main()
