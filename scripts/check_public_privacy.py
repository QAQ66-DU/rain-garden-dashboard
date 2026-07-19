"""Reject private inventory fields and exact coordinates from public/browser artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TARGETS = (
    ROOT / "frontend" / "openapi.json",
    ROOT / "frontend" / "src",
    ROOT / "frontend" / "tests" / "fixtures",
    ROOT / "frontend" / "e2e",
)
FORBIDDEN = (
    "private_latitude",
    "private_longitude",
    "external_device_id",
    "external_event_identifier",
    "raw_payload",
    "channel_metadata",
    "deveui",
    "55.955391",
    "55.955470",
    "55.955613",
    "55.955383",
    "55.955405",
    "55.955528",
    "55.955312",
    "55.955466",
    "-3.238305",
    "-3.237539",
    "-3.236647",
    "-3.238577",
    "-3.237983",
    "-3.237223",
    "-3.238602",
    "-3.239190",
)


def files_to_scan() -> list[Path]:
    files: list[Path] = []
    for target in PUBLIC_TARGETS:
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(path for path in target.rglob("*") if path.is_file())
    return sorted(files)


def main() -> int:
    findings: list[str] = []
    scanned = 0
    for path in files_to_scan():
        try:
            contents = path.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        scanned += 1
        for forbidden in FORBIDDEN:
            if forbidden in contents:
                findings.append(f"{path.relative_to(ROOT)}: contains {forbidden}")
    if findings:
        print("Public privacy check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"Public privacy check passed for {scanned} public/browser files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
