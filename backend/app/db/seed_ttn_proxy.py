from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repositories.ttn_replay import LIVE_MQTT_CONTEXT, ensure_ttn_proxy_inventory
from app.db.session import SessionLocal
from app.db.sync_catalog import sync_metric_catalog


def seed_ttn_proxy_inventory(session: Session) -> None:
    """Create only the approved proxy inventory, without observations or credentials."""

    sync_metric_catalog(session)
    ensure_ttn_proxy_inventory(session, context=LIVE_MQTT_CONTEXT)


def main() -> None:
    with SessionLocal.begin() as session:
        seed_ttn_proxy_inventory(session)
    print("TTN proxy inventory seed completed.")


if __name__ == "__main__":
    main()
