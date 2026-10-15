"""Read-only scan of the HMX Metatype repository.

Usage (from the project root):
    python scripts/scan_metatype_repository.py [HMX_ROOT] [--json REPORT.json]

HMX_ROOT defaults to AppConfig.metatype_repository_root. The JSON report must be
written outside the HMX repository. Nothing in the repository is modified and
no build tool is executed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import AppConfig  # noqa: E402
from models.metatype_scan import ScanStatus  # noqa: E402
from services.metatype.metatype_repository_service import MetatypeRepositoryService  # noqa: E402
from services.metatype.repository_scanner import MetatypeRepositoryScanner, format_scan_summary  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=AppConfig().metatype_repository_root)
    parser.add_argument("--json", dest="json_path", help="write the full report to this file (outside the repository)")
    args = parser.parse_args(argv)

    result = MetatypeRepositoryScanner().scan(args.root)
    print(format_scan_summary(result))
    if args.json_path:
        try:
            written = MetatypeRepositoryService.export_json(result, args.json_path)
        except (OSError, ValueError) as exc:
            print(f"\nCould not write report: {exc}", file=sys.stderr)
            return 2
        print(f"\nReport written to {written}")
    return 1 if result.status is ScanStatus.FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
