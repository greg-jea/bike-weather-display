"""
Snapshot logger — saves raw MeteoSwiss API responses for later replay/backtesting.
Run once each morning (e.g. via cron at 06:55).

Snapshots are saved to ./snapshots/YYYY-MM-DD.json
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

from weather_checker import PLZS, METEOSWISS_URL

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def main():
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    today = datetime.now().astimezone().date().isoformat()
    out_path = SNAPSHOT_DIR / f"{today}.json"

    if out_path.exists():
        print(f"Snapshot for {today} already exists: {out_path}")
        return

    snapshot = {}
    for plz in PLZS:
        try:
            resp = requests.get(METEOSWISS_URL, params={"plz": plz}, timeout=10)
            resp.raise_for_status()
            snapshot[plz] = resp.json()["graph"]
            print(f"  PLZ {plz[:4]} … ok")
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                print(f"  PLZ {plz[:4]} … not in coverage, skipped")
            else:
                print(f"  PLZ {plz[:4]} … HTTP error: {e}", file=sys.stderr)
                sys.exit(1)
        except requests.RequestException as e:
            print(f"  PLZ {plz[:4]} … error: {e}", file=sys.stderr)
            sys.exit(1)

    out_path.write_text(json.dumps(snapshot, indent=2))
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
