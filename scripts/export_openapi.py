import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://contract:contract@localhost/contract")
os.environ.setdefault("TTN_WEBHOOK_ENABLED", "false")
os.environ.setdefault("TTN_WEBHOOK_SECRET", "contract-only-placeholder")

from app.main import app  # noqa: E402


def main() -> None:
    target = ROOT / "frontend" / "openapi.json"
    target.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

