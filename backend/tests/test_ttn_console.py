import json
from pathlib import Path

from app.ingestion.ttn_console import FORWARD_EVENT_NAME, parse_console_export_event

FIXTURE = Path(__file__).parent / "fixtures" / "ttn" / "outflow-a-redacted.json"


def test_redacted_fixture_covers_normal_status_invalid_and_ignored_events() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    events = fixture["events"]

    assert fixture["fixture_metadata"]["synthetic_identifiers"] is True
    assert len(events) == 4
    assert [event["name"] for event in events].count(FORWARD_EVENT_NAME) == 3
    assert parse_console_export_event(events[-1]) is None

    normal = parse_console_export_event(events[0])
    status = parse_console_export_event(events[1])
    invalid = parse_console_export_event(events[2])
    assert normal is not None and status is not None and invalid is not None
    assert normal.application_id == "synthetic-rain-garden"
    assert normal.device_id == "synthetic-outflow-a"
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


def test_redacted_fixture_contains_no_local_private_fixture_or_credential_markers() -> None:
    serialized = FIXTURE.read_text(encoding="utf-8")

    assert "NNSXS." not in serialized
    assert "outflow-a@" not in serialized
    assert "rain-garden@" not in serialized
    assert "synthetic-session-key-id" in serialized
