import argparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.seed import SITE_ID, seed_session
from app.db.session import SessionLocal
from app.db.synthetic import KNOWN_SYNTHETIC_EXTERNAL_IDS
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.monitoring_feature import MonitoringFeature
from app.models.sensor_channel import SensorChannel
from app.models.site import Site
from app.models.uplink_event import UplinkEvent


class DemoResetRefused(RuntimeError):
    """The requested reset does not satisfy the demo-only safety boundary."""


def validate_reset_environment(settings: Settings, *, confirmed: bool) -> None:
    if not confirmed:
        raise DemoResetRefused("Pass --confirm-reset to acknowledge the destructive demo reset.")
    if not settings.demo_mode or settings.app_env == "production":
        raise DemoResetRefused("Demo reset is allowed only in development or test demo mode.")


def reset_demo_session(session: Session) -> bool:
    site = session.get(Site, SITE_ID)
    if site is None:
        return False
    devices = list(session.scalars(select(Device).where(Device.site_id == SITE_ID)))
    external_ids = {device.external_device_id for device in devices}
    if not external_ids.issubset(KNOWN_SYNTHETIC_EXTERNAL_IDS):
        raise DemoResetRefused(
            "Orchard Park contains devices not owned by the deterministic demo seed."
        )
    device_ids = [device.id for device in devices]
    if device_ids:
        sources = set(
            session.scalars(
                select(UplinkEvent.source).where(UplinkEvent.device_id.in_(device_ids)).distinct()
            )
        )
        if not sources.issubset({"synthetic"}):
            raise DemoResetRefused("Orchard Park contains non-synthetic uplinks.")
        session.execute(delete(Measurement).where(Measurement.device_id.in_(device_ids)))
        session.execute(delete(UplinkEvent).where(UplinkEvent.device_id.in_(device_ids)))
        session.execute(delete(SensorChannel).where(SensorChannel.device_id.in_(device_ids)))
        session.execute(delete(Device).where(Device.id.in_(device_ids)))
    session.execute(delete(MonitoringFeature).where(MonitoringFeature.site_id == SITE_ID))
    session.execute(delete(Site).where(Site.id == SITE_ID))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset only the deterministic demo dataset")
    parser.add_argument("--confirm-reset", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    validate_reset_environment(settings, confirmed=args.confirm_reset)
    with SessionLocal.begin() as session:
        removed = reset_demo_session(session)
        session.flush()
        seed_session(session)
    if removed:
        print("Removed the owned deterministic demo dataset; reseeding confirmed inventory.")
    else:
        print("No deterministic demo dataset was present; seeding confirmed inventory.")
    print("Seeded the confirmed Orchard Park inventory in the same database transaction.")


if __name__ == "__main__":
    main()
