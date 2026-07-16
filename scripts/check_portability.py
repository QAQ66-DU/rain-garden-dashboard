"""Reject platform-specific runtime dependencies and developer-machine paths."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIRECTORIES = ("backend/app", "frontend/src", "db/init")
RUNTIME_FILES = (
    ".env.example",
    "backend/Dockerfile",
    "backend/pyproject.toml",
    "backend/uv.lock",
    "docker-compose.yml",
    "frontend/Dockerfile",
    "frontend/package-lock.json",
    "frontend/package.json",
    "frontend/nginx.conf",
)
FORBIDDEN = {
    "Replit runtime dependency": re.compile(
        r"(?i)(?:from|import)\s+replit\b|@replit/|replit\.nix|(?:^|/)\.replit(?:$|/)"
    ),
    "developer-machine path": re.compile(r"/Users/|/home/runner/|[A-Za-z]:\\Users\\"),
}


def candidate_files() -> list[Path]:
    files = [ROOT / relative for relative in RUNTIME_FILES]
    for relative in RUNTIME_DIRECTORIES:
        files.extend(path for path in (ROOT / relative).rglob("*") if path.is_file())
    return sorted(set(files))


def main() -> int:
    findings: list[str] = []
    scanned = 0
    for path in candidate_files():
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for label, pattern in FORBIDDEN.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}")

    if findings:
        print("Portability check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print(f"Portability check passed for {scanned} runtime and configuration files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
