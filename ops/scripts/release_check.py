"""Run the new release's readiness route before changing the current symlink."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from passenger_wsgi import application


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    with application.test_client() as client:
        response = client.get("/health/ready", base_url=args.base_url.rstrip("/"))
    if response.status_code != 200 or not response.is_json or not response.json.get("ok"):
        raise RuntimeError(
            f"release readiness failed with status {response.status_code}"
        )
    print("release readiness: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
