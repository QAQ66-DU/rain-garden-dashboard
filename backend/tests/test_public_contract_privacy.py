import json

from app.core.config import Settings
from app.main import create_app


def test_generated_public_contract_excludes_private_inventory_fields() -> None:
    settings = Settings(database_url="postgresql+psycopg://contract:contract@db/contract")
    contract_text = json.dumps(create_app(settings).openapi()).lower()

    for forbidden in (
        "private_latitude",
        "private_longitude",
        "external_device_id",
        "external_event_identifier",
        "raw_payload",
        "channel_metadata",
        "deveui",
        "55.955391",
        "-3.238305",
    ):
        assert forbidden not in contract_text

    assert "unit_confirmation_status" in contract_text
    assert "unit_unconfirmed" not in contract_text
