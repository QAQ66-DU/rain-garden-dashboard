import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.metric_catalog import render_data_dictionary  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the metric data dictionary")
    parser.add_argument("--check", action="store_true", help="fail if the generated file is stale")
    args = parser.parse_args()
    target = ROOT / "docs" / "data-dictionary.md"
    rendered = render_data_dictionary()
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != rendered:
            print("docs/data-dictionary.md is out of date", file=sys.stderr)
            return 1
        return 0
    target.write_text(rendered, encoding="utf-8")
    print(f"Wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

