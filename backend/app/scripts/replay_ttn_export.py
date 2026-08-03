from __future__ import annotations

import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.ttn_replay import replay_ttn_export


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay a local TTN Live Data console export without network access."
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if not args.path.is_file():
        parser.error("the replay input path must be an existing file")

    with SessionLocal.begin() as session:
        summary = replay_ttn_export(session, args.path)

    print(f"Total console events: {summary.total_events}")
    print(f"Selected as.up.data.forward: {summary.selected_uplinks}")
    print(f"Raw uplinks inserted: {summary.raw_inserted}")
    print(f"Duplicates skipped: {summary.duplicates_skipped}")
    print(f"Measurements created: {summary.measurements_created}")
    print(f"Invalid decoded uplinks preserved: {summary.invalid_preserved}")
    print(f"Status blocks processed: {summary.status_processed}")
    print(f"Quarantined: {summary.quarantined}")
    print(f"Failed: {summary.failed}")


if __name__ == "__main__":
    main()
