from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.seed_ttn_proxy import seed_ttn_proxy_inventory
from app.db.session import SessionLocal
from app.ingestion.ttn_mqtt import MQTTConfigurationError, MQTTMessageProcessor, run_mqtt_worker
from app.services.ttn_ingestion import TTNIngestionService

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    with SessionLocal.begin() as session:
        seed_ttn_proxy_inventory(session)
    processor = MQTTMessageProcessor(
        TTNIngestionService(SessionLocal.begin),
        max_payload_bytes=settings.webhook_body_limit_bytes,
    )
    try:
        run_mqtt_worker(settings, processor=processor)
    except MQTTConfigurationError as exc:
        logger.error(str(exc))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
