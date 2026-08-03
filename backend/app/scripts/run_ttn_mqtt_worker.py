from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ingestion.ttn_mqtt import MQTTConfigurationError, run_mqtt_worker

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        run_mqtt_worker(settings)
    except MQTTConfigurationError as exc:
        logger.error(str(exc))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
