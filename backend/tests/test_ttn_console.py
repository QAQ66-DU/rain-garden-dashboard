import copy
import json
from pathlib import Path

import pytest
from app.ingestion.ttn_console import (
    FORWARD_EVENT_NAME,
    normalise_application_up,
    parse_console_export_event,
)

FIXTURE = Path(__file__).parent / "fixtures" / "ttn" / "outflow-a-redacted.json"


def test_redacted_fixture_covers_normal_status_invalid_and_ignored_events() -> None:
    fixture = copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8")))
    events = fixture["events"]
    for event in events:
        if event.get("name") != FORWARD_EVENT_NAME:
            continue
        event["data"]["end_device_ids"]["device_id"] = "outflow-a"
        event["data"]["end_device_ids"]["application_ids"]["application_id"] = "rain-garden"

    assert fixture["fixture_metadata"]["synthetic_identifiers"] is True
    assert len(events) == 4
    assert [event["name"] for event in events].count(FORWARD_EVENT_NAME) == 3
    assert parse_console_export_event(events[-1]) is None

    normal = parse_console_export_event(events[0])
    status = parse_console_export_event(events[1])
    invalid = parse_console_export_event(events[2])
    assert normal is not None and status is not None and invalid is not None
    assert normal.application_id == "rain-garden"
    assert normal.device_id == "outflow-a"
    assert [(item.measurement_id, int(item.value)) for item in normal.measurements] == [
        (1, 840),
        (2, 200),
    ]
    assert status.status is not None
    assert status.status.firmware_version == "3.0"
    assert status.status.hardware_version == "1.1"
    assert status.status.measurement_interval_value is not None
    assert invalid.decoded_valid is False
    assert invalid.invalid_reason == "decoded_payload_not_valid"
    assert invalid.measurements == ()


def test_supported_outflow_identity_uses_the_same_redacted_payload_shape() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    event = copy.deepcopy(fixture["events"][0])
    event["data"]["end_device_ids"]["device_id"] = "outflow-a"
    event["data"]["end_device_ids"]["application_ids"]["application_id"] = "rain-garden"

    normal = parse_console_export_event(event)

    assert normal is not None
    assert [(item.measurement_id, int(item.value)) for item in normal.measurements] == [
        (1, 840),
        (2, 200),
    ]


@pytest.mark.parametrize("invalid_value", ["not-numeric", "NaN", "Infinity"])
def test_non_finite_or_non_numeric_measurements_are_rejected(invalid_value: str) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    application_up = copy.deepcopy(fixture["events"][0]["data"])
    application_up["end_device_ids"]["device_id"] = "outflow-a"
    application_up["end_device_ids"]["application_ids"]["application_id"] = "rain-garden"
    application_up["uplink_message"]["decoded_payload"]["messages"][0][0]["measurementValue"] = (
        invalid_value
    )

    uplink = normalise_application_up(application_up, raw_event=application_up)

    assert uplink.decoded_valid is False
    assert uplink.invalid_reason == "malformed_measurement"
    assert uplink.measurements == ()


def test_redacted_fixture_contains_no_local_private_fixture_or_credential_markers() -> None:
    serialized = FIXTURE.read_text(encoding="utf-8")

    assert "NNSXS." not in serialized
    assert "outflow-a@" not in serialized
    assert "rain-garden@" not in serialized
    assert "synthetic-session-key-id" in serialized


@pytest.mark.parametrize(
    ("device_id", "measurement_ids"),
    [
        ("soil-moisture-1", [1]),
        ("weather-station-2", [4097, 4098, 4099, 4190, 4105, 4104, 4113, 4101]),
        ("weather-station", [4097, 4098, 4099, 4190, 4105, 4104, 4113, 4101]),
        ("ph-sensor", [4097, 4106]),
        ("soilmoisture-temp-sensor", [4102, 4103, 4108]),
    ],
)
def test_supplied_formatter_shapes_normalise_only_approved_channels(
    device_id: str,
    measurement_ids: list[int],
) -> None:
    path = FIXTURE.parent / f"{device_id}-redacted.json"
    application_up = json.loads(path.read_text(encoding="utf-8"))

    uplink = normalise_application_up(application_up, raw_event=application_up)

    assert uplink.device_id == device_id
    assert uplink.decoded_valid is True
    assert [item.measurement_id for item in uplink.measurements] == measurement_ids


@pytest.mark.parametrize("device_id", ["prototype-board-1", "vision-ai"])
def test_no_uplink_exports_remain_explicitly_empty(device_id: str) -> None:
    path = FIXTURE.parent / f"{device_id}-redacted.json"

    assert json.loads(path.read_text(encoding="utf-8")) == []
