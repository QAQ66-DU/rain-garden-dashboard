import csv
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO
from typing import Any, Protocol, cast
from uuid import UUID

import pytest
from app.core.config import Settings
from app.db.seed import SITE_ID, seed_session
from app.db.synthetic import stable_uuid
from app.models.measurement import Measurement
from app.models.sensor_channel import SensorChannel
from app.models.uplink_event import UplinkEvent
from app.services.errors import ServiceError
from app.services.measurements import list_measurements
from sqlalchemy import insert
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration

WEATHER_DEVICE_ID = stable_uuid("device:synthetic-v2-swale-weather-001")
TREE_PROBE_ID = stable_uuid("device:synthetic-v2-tree-pit-probe-001")


class ClientResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]
    text: str

    def json(self) -> Any: ...


def _weather_channel_id(api_client: TestClient, channel_code: str = "rainfall_intensity") -> str:
    detail = api_client.get(f"/api/v1/devices/{WEATHER_DEVICE_ID}")
    assert detail.status_code == 200
    return str(
        next(
            channel["id"]
            for channel in detail.json()["channels"]
            if channel["channel_code"] == channel_code
        )
    )


def _export_measurements(
    api_client: TestClient,
    *,
    start: str,
    end: str,
    device_id: UUID = WEATHER_DEVICE_ID,
    channel_id: str | None = None,
) -> ClientResponse:
    return cast(
        ClientResponse,
        api_client.get(
            f"/api/v1/devices/{device_id}/measurements/export.csv",
            params={
                "start": start,
                "end": end,
                "sensor_channel_id": channel_id or _weather_channel_id(api_client),
            },
        ),
    )


def test_health_and_security_headers(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/health", headers={"X-Request-ID": "integration-check"})

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.headers["x-request-id"] == "integration-check"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_overview_is_channel_aware_and_synthetic(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/overview", params={"site_id": str(SITE_ID)})

    assert response.status_code == 200
    body = response.json()
    assert body["synthetic"] is True
    assert body["devices"] == {
        "total": 8,
        "online": 3,
        "stale": 2,
        "offline": 2,
        "unknown": 1,
    }
    assert body["data_quality"]["warning_count"] == 1
    soil = body["soil_moisture"]
    assert "average" not in soil
    assert soil["contributing_channel_count"] == 3
    assert [channel["depth_cm"] for channel in soil["contributing_channels"]] == [None] * 3
    assert soil["minimum"] <= soil["median"] <= soil["maximum"]


def test_public_responses_exclude_private_fields(api_client: TestClient) -> None:
    site = api_client.get(f"/api/v1/sites/{SITE_ID}")
    devices = api_client.get("/api/v1/devices", params={"site_id": str(SITE_ID)})
    detail = api_client.get(f"/api/v1/devices/{WEATHER_DEVICE_ID}")

    assert site.status_code == devices.status_code == detail.status_code == 200
    serialized = f"{site.text}\n{devices.text}\n{detail.text}"
    for forbidden in (
        "external_device_id",
        "raw_payload",
        "private_latitude",
        "private_longitude",
        "channel_metadata",
        "DevEUI",
        "synthetic-v2-swale-weather-001",
    ):
        assert forbidden not in serialized


def test_measurement_cursor_is_deterministic(api_client: TestClient) -> None:
    first = api_client.get(
        f"/api/v1/devices/{WEATHER_DEVICE_ID}/measurements",
        params={"metric_code": "rainfall_intensity", "page_size": 3},
    )

    assert first.status_code == 200
    first_body = first.json()
    assert first_body["total_matching"] == 168
    assert len(first_body["items"]) == 3
    assert first_body["next_cursor"] is not None
    assert all(item["unit_symbol"] == "mm/h" for item in first_body["items"])
    assert all(
        item["unit_confirmation_status"] == "synthetic_demo_only" for item in first_body["items"]
    )

    second = api_client.get(
        f"/api/v1/devices/{WEATHER_DEVICE_ID}/measurements",
        params={
            "metric_code": "rainfall_intensity",
            "page_size": 3,
            "cursor": first_body["next_cursor"],
        },
    )
    assert second.status_code == 200
    assert datetime.fromisoformat(
        second.json()["items"][0]["measured_at"]
    ) > datetime.fromisoformat(first_body["items"][-1]["measured_at"])


def test_measurement_chart_returns_every_point_below_display_threshold(
    api_client: TestClient,
) -> None:
    channel_id = _weather_channel_id(api_client)
    response = api_client.get(
        f"/api/v1/devices/{WEATHER_DEVICE_ID}/measurements/chart",
        params={
            "start": "2026-05-31T12:00:00Z",
            "end": "2026-06-01T12:00:00Z",
            "sensor_channel_id": channel_id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_matching"] == 24
    assert body["points_returned"] == 24
    assert body["downsampling_applied"] is False
    assert len(body["items"]) == 24


def test_large_chart_is_bounded_shape_preserving_and_csv_remains_complete(
    api_client: TestClient, db_session: Session
) -> None:
    channel_id = UUID(_weather_channel_id(api_client))
    start = datetime(2026, 6, 2, tzinfo=UTC)
    count = 5_001
    timestamps = [start + timedelta(seconds=index * 5) for index in range(count)]
    event_ids = [stable_uuid(f"chart-sampling-event:{index}") for index in range(count)]
    values = [
        Decimal("999")
        if index == 1_111
        else Decimal("-999")
        if index == 3_333
        else Decimal(index % 23)
        for index in range(count)
    ]
    db_session.execute(
        insert(UplinkEvent),
        [
            {
                "id": event_id,
                "device_id": WEATHER_DEVICE_ID,
                "source": "chart-sampling-test",
                "idempotency_key": f"chart-sampling-{index}",
                "received_at": timestamp,
                "measured_at": timestamp,
                "raw_payload": {},
                "ingestion_status": "accepted",
                "ingestion_mode": "live_mqtt",
                "provenance": "proxy",
            }
            for index, (event_id, timestamp) in enumerate(zip(event_ids, timestamps, strict=True))
        ],
    )
    db_session.execute(
        insert(Measurement),
        [
            {
                "id": stable_uuid(f"chart-sampling-measurement:{index}"),
                "uplink_event_id": event_id,
                "device_id": WEATHER_DEVICE_ID,
                "sensor_channel_id": channel_id,
                "numeric_value": value,
                "measured_at": timestamp,
                "quality_flag": "valid",
            }
            for index, (event_id, timestamp, value) in enumerate(
                zip(event_ids, timestamps, values, strict=True)
            )
        ],
    )
    db_session.flush()
    end = timestamps[-1] + timedelta(microseconds=1)
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "sensor_channel_id": str(channel_id),
    }

    raw = api_client.get(
        f"/api/v1/devices/{WEATHER_DEVICE_ID}/measurements",
        params={**params, "page_size": 500},
    )
    chart = api_client.get(f"/api/v1/devices/{WEATHER_DEVICE_ID}/measurements/chart", params=params)
    exported = api_client.get(
        f"/api/v1/devices/{WEATHER_DEVICE_ID}/measurements/export.csv", params=params
    )

    assert raw.status_code == 422
    assert raw.json()["error_code"] == "result_set_too_large"
    assert chart.status_code == 200
    body = chart.json()
    assert body["total_matching"] == count
    assert body["points_returned"] == len(body["items"])
    assert body["points_returned"] <= 2_000
    assert body["downsampling_applied"] is True
    assert {item["channel_id"] for item in body["items"]} == {str(channel_id)}
    observed_times = [item["measured_at"] for item in body["items"]]
    assert observed_times == sorted(observed_times)
    assert observed_times[0] == timestamps[0].isoformat().replace("+00:00", "Z")
    assert observed_times[-1] == timestamps[-1].isoformat().replace("+00:00", "Z")
    assert {item["numeric_value"] for item in body["items"]}.issuperset({-999.0, 999.0})

    assert exported.status_code == 200
    exported_rows = list(csv.DictReader(StringIO(exported.text)))
    assert len(exported_rows) == count
    assert exported_rows[0]["observed_at"] == observed_times[0]
    assert exported_rows[-1]["observed_at"] == observed_times[-1]


@pytest.mark.parametrize(
    ("start", "end", "expected_rows"),
    (
        ("2026-05-31T12:00:00Z", "2026-06-01T12:00:00Z", 24),
        ("2026-05-25T12:00:00Z", "2026-06-01T12:00:00Z", 168),
        ("2026-05-02T12:00:00Z", "2026-06-01T12:00:00Z", 168),
        ("2026-05-31T09:00:00Z", "2026-05-31T12:00:00Z", 3),
    ),
)
def test_measurement_csv_export_accepts_preset_and_custom_windows(
    api_client: TestClient, start: str, end: str, expected_rows: int
) -> None:
    response = _export_measurements(api_client, start=start, end=end)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="swale-weather-station_rainfall-intensity_'
        f'{start[:10]}_{end[:10]}.csv"'
    )
    rows = list(csv.DictReader(StringIO(response.text)))
    assert len(rows) == expected_rows


def test_measurement_csv_export_is_half_open_precise_and_privacy_safe(
    api_client: TestClient,
) -> None:
    channel_id = _weather_channel_id(api_client)
    response = _export_measurements(
        api_client,
        start="2026-05-31T11:00:00+00:00",
        end="2026-05-31T12:00:00+00:00",
        channel_id=channel_id,
    )

    assert response.status_code == 200
    reader = csv.DictReader(StringIO(response.text))
    assert reader.fieldnames == [
        "observed_at",
        "device_id",
        "device_name",
        "channel_id",
        "channel_name",
        "measurement_value",
        "unit_code",
        "unit_confirmation_status",
        "verification_status",
        "quality_flag",
        "ingestion_mode",
        "provenance",
    ]
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["observed_at"] == "2026-05-31T11:00:00Z"
    assert rows[0]["device_id"] == str(WEATHER_DEVICE_ID)
    assert rows[0]["device_name"] == "Swale weather station"
    assert rows[0]["channel_id"] == channel_id
    assert rows[0]["channel_name"] == "Rainfall intensity"
    assert rows[0]["measurement_value"].endswith("000000")
    assert rows[0]["unit_code"] == "mm_h"
    assert rows[0]["unit_confirmation_status"] == "synthetic_demo_only"
    assert rows[0]["verification_status"] == "catalogued"
    assert rows[0]["quality_flag"] in {"valid", "out_of_range", "suspect"}
    serialized = response.text.lower()
    for forbidden in (
        "raw_payload",
        "external_device_id",
        "deveui",
        "joineui",
        "devaddr",
        "gateway",
        "session_key",
        "private_latitude",
        "private_longitude",
    ):
        assert forbidden not in serialized


def test_measurement_csv_export_returns_headers_for_empty_window(api_client: TestClient) -> None:
    response = _export_measurements(
        api_client,
        start="2026-05-01T00:00:00Z",
        end="2026-05-01T01:00:00Z",
    )

    assert response.status_code == 200
    assert len(list(csv.reader(StringIO(response.text)))) == 1


@pytest.mark.parametrize(
    ("params", "error_code"),
    (
        (
            {"start": "2026-05-31T11:00:00Z", "end": "2026-05-31T11:00:00Z"},
            "invalid_time_range",
        ),
        ({"start": "not-a-timestamp", "end": "2026-05-31T12:00:00Z"}, "validation_error"),
        ({"start": "2026-05-31T11:00:00Z"}, "validation_error"),
        ({"end": "2026-05-31T12:00:00Z"}, "validation_error"),
    ),
)
def test_measurement_csv_export_rejects_invalid_ranges(
    api_client: TestClient, params: dict[str, str], error_code: str
) -> None:
    response = api_client.get(
        f"/api/v1/devices/{WEATHER_DEVICE_ID}/measurements/export.csv",
        params={"sensor_channel_id": _weather_channel_id(api_client), **params},
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == error_code


def test_measurement_csv_export_rejects_channel_from_another_device(
    api_client: TestClient,
) -> None:
    response = _export_measurements(
        api_client,
        start="2026-05-31T11:00:00Z",
        end="2026-05-31T12:00:00Z",
        device_id=TREE_PROBE_ID,
        channel_id=_weather_channel_id(api_client),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "channel_not_found"


def test_oversized_raw_result_is_rejected(db_session: Session) -> None:
    seed_session(db_session)
    settings = Settings(
        database_url="postgresql+psycopg://test:test@localhost/test",
        max_measurement_result_rows=10,
    )

    with pytest.raises(ServiceError) as error:
        list_measurements(
            db_session,
            settings,
            WEATHER_DEVICE_ID,
            start=datetime(2026, 5, 25, 12, tzinfo=UTC),
            end=datetime(2026, 6, 1, 12, tzinfo=UTC),
            metric_code="rainfall_intensity",
            sensor_channel_id=None,
            page_size=10,
            cursor=None,
        )

    assert error.value.error_code == "result_set_too_large"
    assert "168 rows" in error.value.detail


def test_confirmed_inventory_features_and_pending_tree_probe(api_client: TestClient) -> None:
    devices = api_client.get("/api/v1/devices", params={"page_size": 100, "site_id": str(SITE_ID)})
    tree = api_client.get(f"/api/v1/devices/{TREE_PROBE_ID}")

    assert devices.status_code == tree.status_code == 200
    body = devices.json()
    assert len(body["items"]) == 8
    assert {item["monitoring_feature"]["display_name"] for item in body["items"]} == {
        "Swale",
        "Tree pit",
    }
    tree_body = tree.json()
    assert tree_body["sensor_configuration_status"] == "pending"
    assert tree_body["channels"] == []
    assert tree_body["latest_measurements"] == []


def test_feature_filter_returns_only_swale_devices(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/devices", params={"feature": "swale", "site_id": str(SITE_ID)}
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 7
    assert all(
        item["monitoring_feature"]["feature_type"] == "swale" for item in response.json()["items"]
    )


def test_webhook_authentication_and_disabled_adapter(api_client: TestClient) -> None:
    missing = api_client.post("/api/v1/ingestion/ttn", json={})
    wrong = api_client.post(
        "/api/v1/ingestion/ttn",
        json={},
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    accepted_auth = api_client.post(
        "/api/v1/ingestion/ttn",
        json={},
        headers={"X-Webhook-Secret": "integration-test-webhook-secret"},
    )

    assert missing.status_code == wrong.status_code == 401
    assert accepted_auth.status_code == 501
    assert accepted_auth.json()["error_code"] == "ttn_adapter_disabled"


def test_webhook_content_type_and_body_size_are_enforced(api_client: TestClient) -> None:
    headers = {"X-Webhook-Secret": "integration-test-webhook-secret"}
    wrong_type = api_client.post("/api/v1/ingestion/ttn", content="not-json", headers=headers)
    oversized = api_client.post(
        "/api/v1/ingestion/ttn", json={"blob": "x" * 2_000}, headers=headers
    )

    assert wrong_type.status_code == 415
    assert oversized.status_code == 413
    assert oversized.json()["error_code"] == "request_body_too_large"


def test_validation_error_uses_problem_contract(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/devices", params={"page_size": 0})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["correlation_id"]
    assert "traceback" not in response.text.lower()


def test_explorer_uses_half_open_periods_and_schedule_aligned_coverage(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2026-05-25T12:00:00Z",
            "end": "2026-06-01T12:00:00Z",
            "metric_group": "hydrology",
            "site_id": str(SITE_ID),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["time_window_semantics"].startswith("Half-open UTC interval [start, end)")
    assert body["total_matching"] == sum(item["total_matching"] for item in body["series"])
    assert body["points_returned"] == sum(item["points_returned"] for item in body["series"])
    assert body["downsampling_applied"] is False
    assert len(body["available_devices"]) == 8
    assert len(body["available_channels"]) == 4
    assert len(body["series"]) == 4
    rainfall = next(
        item for item in body["series"] if item["channel"]["metric_code"] == "rainfall_intensity"
    )
    assert len(rainfall["points"]) == 168
    assert rainfall["total_matching"] == 168
    assert rainfall["points_returned"] == 168
    assert rainfall["downsampling_applied"] is False
    assert rainfall["coverage"] == {
        "status": "available",
        "status_detail": (
            "Coverage counts unique schedule-aligned slots in the half-open UTC window [start, "
            "end); flagged slots are received but not valid. Late means received more than "
            "one reporting interval after measured_at."
        ),
        "expected_observations": 168,
        "received_observations": 168,
        "valid_observations": 168,
        "flagged_observations": 0,
        "missing_observations": 0,
        "coverage_percentage": 100.0,
        "late_observations": 0,
        "out_of_tolerance_observations": 0,
        "duplicate_slot_observations": 0,
        "missing_intervals": [],
    }
    duration = next(
        item
        for item in rainfall["summary"]["statistics"]
        if item["code"] == "duration_above_zero_seconds"
    )
    assert duration["value"] == 21_600
    assert body["quality_warnings"][0]["quality_flag"] == "out_of_range"
    assert body["quality_warnings"][0]["excluded_from_summaries"] is True
    serialized_warning = str(body["quality_warnings"][0]).lower()
    assert "raw_payload" not in serialized_warning
    assert "external_device" not in serialized_warning

    measurements = api_client.get(
        f"/api/v1/devices/{WEATHER_DEVICE_ID}/measurements",
        params={
            "start": "2026-05-25T12:00:00Z",
            "end": "2026-06-01T12:00:00Z",
            "sensor_channel_id": rainfall["channel"]["channel_id"],
            "page_size": 500,
        },
    )
    assert measurements.status_code == 200
    assert measurements.json()["total_matching"] == rainfall["coverage"]["received_observations"]
    assert {
        (item["measured_at"], item["numeric_value"], item["quality_flag"])
        for item in measurements.json()["items"]
    } == {
        (item["measured_at"], item["numeric_value"], item["quality_flag"])
        for item in rainfall["points"]
    }


def test_explorer_samples_large_series_independently_without_mixing(
    api_client: TestClient, db_session: Session
) -> None:
    catalogue = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2026-05-25T12:00:00Z",
            "end": "2026-06-01T12:00:00Z",
            "metric_group": "soil",
            "site_id": str(SITE_ID),
        },
    )
    assert catalogue.status_code == 200
    selected_channels: list[dict[str, str]] = []
    selected_devices: set[str] = set()
    for channel in catalogue.json()["available_channels"]:
        if channel["device_id"] in selected_devices:
            continue
        selected_channels.append(channel)
        selected_devices.add(channel["device_id"])
        if len(selected_channels) == 2:
            break
    assert len(selected_channels) == 2

    start = datetime(2026, 6, 3, tzinfo=UTC)
    observations_per_series = 5_001
    event_rows: list[dict[str, object]] = []
    measurement_rows: list[dict[str, object]] = []
    expected_ids: dict[str, set[str]] = {}
    for series_index, channel in enumerate(selected_channels):
        channel_id = UUID(channel["channel_id"])
        device_id = UUID(channel["device_id"])
        series_ids: set[str] = set()
        for observation_index in range(observations_per_series):
            observed_at = start + timedelta(seconds=observation_index * 5)
            event_id = stable_uuid(f"explorer-sampling-event:{channel_id}:{observation_index}")
            measurement_id = stable_uuid(
                f"explorer-sampling-measurement:{channel_id}:{observation_index}"
            )
            numeric_value = (
                Decimal(1_000 + series_index)
                if observation_index == 1_111
                else Decimal(-1_000 - series_index)
                if observation_index == 3_333
                else Decimal((observation_index % 23) + series_index * 100)
            )
            event_rows.append(
                {
                    "id": event_id,
                    "device_id": device_id,
                    "source": "explorer-sampling-test",
                    "idempotency_key": f"{channel_id}:{observation_index}",
                    "received_at": observed_at,
                    "measured_at": observed_at,
                    "raw_payload": {},
                    "ingestion_status": "accepted",
                    "ingestion_mode": "live_mqtt",
                    "provenance": "proxy",
                }
            )
            measurement_rows.append(
                {
                    "id": measurement_id,
                    "uplink_event_id": event_id,
                    "device_id": device_id,
                    "sensor_channel_id": channel_id,
                    "numeric_value": numeric_value,
                    "measured_at": observed_at,
                    "quality_flag": "valid",
                }
            )
            series_ids.add(str(measurement_id))
        expected_ids[str(channel_id)] = series_ids

    db_session.execute(insert(UplinkEvent), event_rows)
    db_session.execute(insert(Measurement), measurement_rows)
    db_session.flush()
    end = start + timedelta(seconds=(observations_per_series - 1) * 5, microseconds=1)
    response = api_client.get(
        "/api/v1/explore",
        params={
            "start": start.isoformat(),
            "end": end.isoformat(),
            "metric_group": "soil",
            "channels": ",".join(channel["channel_id"] for channel in selected_channels),
            "site_id": str(SITE_ID),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_matching"] == observations_per_series * 2
    assert body["points_returned"] == sum(item["points_returned"] for item in body["series"])
    assert body["downsampling_applied"] is True
    assert len(body["series"]) == 2
    assert {item["channel"]["device_id"] for item in body["series"]} == selected_devices
    for series_index, series in enumerate(body["series"]):
        assert series["total_matching"] == observations_per_series
        assert series["points_returned"] == len(series["points"])
        assert series["points_returned"] <= 2_000
        assert series["downsampling_applied"] is True
        channel_id = series["channel"]["channel_id"]
        assert {point["measurement_id"] for point in series["points"]} <= expected_ids[channel_id]
        observed_times = [point["measured_at"] for point in series["points"]]
        assert observed_times == sorted(observed_times)
        assert observed_times[0] == start.isoformat().replace("+00:00", "Z")
        assert observed_times[-1] == end.isoformat().replace("+00:00", "Z").replace(".000001Z", "Z")
        assert {point["numeric_value"] for point in series["points"]}.issuperset(
            {-1_000.0 - series_index, 1_000.0 + series_index}
        )


def test_explorer_feature_and_channel_selection_are_explicit(api_client: TestClient) -> None:
    tree = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2026-05-25T12:00:00Z",
            "end": "2026-06-01T12:00:00Z",
            "feature": "tree-pit",
            "metric_group": "soil",
            "site_id": str(SITE_ID),
        },
    )
    assert tree.status_code == 200
    assert len(tree.json()["available_devices"]) == 1
    assert tree.json()["available_channels"] == []
    assert tree.json()["series"] == []

    hydrology = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2026-05-25T12:00:00Z",
            "end": "2026-06-01T12:00:00Z",
            "metric_group": "hydrology",
            "site_id": str(SITE_ID),
        },
    ).json()
    channel_id = hydrology["available_channels"][0]["channel_id"]
    selected = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2026-05-25T12:00:00Z",
            "end": "2026-06-01T12:00:00Z",
            "metric_group": "hydrology",
            "channels": channel_id,
            "site_id": str(SITE_ID),
        },
    )
    assert selected.status_code == 200
    assert selected.json()["selected_channel_ids"] == [channel_id]
    assert len(selected.json()["series"]) == 1


def test_explorer_empty_period_reports_missing_slots_without_zero_fill(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2026-05-01T12:00:00Z",
            "end": "2026-05-01T13:00:00Z",
            "metric_group": "hydrology",
            "site_id": str(SITE_ID),
        },
    )

    assert response.status_code == 200
    for series in response.json()["series"]:
        assert series["points"] == []
        assert series["summary"]["status"] == "no_data"
        assert series["coverage"]["expected_observations"] == 1
        assert series["coverage"]["received_observations"] == 0
        assert series["coverage"]["missing_observations"] == 1
        assert series["coverage"]["coverage_percentage"] == 0


def test_explorer_does_not_infer_unknown_reporting_schedule(
    api_client: TestClient, db_session: Session
) -> None:
    initial = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2026-05-25T12:00:00Z",
            "end": "2026-05-25T13:00:00Z",
            "metric_group": "hydrology",
            "site_id": str(SITE_ID),
        },
    ).json()
    channel_id = initial["available_channels"][0]["channel_id"]
    channel = db_session.get(SensorChannel, UUID(channel_id))
    assert channel is not None
    channel.expected_reporting_interval_seconds = None
    channel.reporting_schedule_anchor_at = None
    channel.reporting_jitter_tolerance_seconds = None
    db_session.flush()

    response = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2026-05-25T12:00:00Z",
            "end": "2026-05-25T13:00:00Z",
            "metric_group": "hydrology",
            "channels": channel_id,
            "site_id": str(SITE_ID),
        },
    )

    assert response.status_code == 200
    coverage = response.json()["series"][0]["coverage"]
    assert coverage["status"] == "unavailable"
    assert coverage["expected_observations"] is None
    assert coverage["coverage_percentage"] is None


@pytest.mark.parametrize(
    ("start", "end", "error_code"),
    (
        ("2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "invalid_time_range"),
        ("2026-04-01T00:00:00Z", "2026-06-01T12:00:00Z", "time_range_too_large"),
    ),
)
def test_explorer_rejects_invalid_periods(
    api_client: TestClient, start: str, end: str, error_code: str
) -> None:
    response = api_client.get(
        "/api/v1/explore",
        params={
            "start": start,
            "end": end,
            "metric_group": "hydrology",
            "site_id": str(SITE_ID),
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == error_code
