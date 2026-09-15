"""
Replay a saved snapshot through the decision logic.

Usage:
    python3 replay_snapshot.py 2026-06-09
    python3 replay_snapshot.py          # replays all snapshots
"""

import json
import sys
from datetime import date
from pathlib import Path

from weather_checker import decide, DISPLAY, LCD_CODE, SEVERITY

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def replay(date_str: str):
    path = SNAPSHOT_DIR / f"{date_str}.json"
    if not path.exists():
        print(f"No snapshot for {date_str}")
        return

    snapshot = json.loads(path.read_text())
    print(f"\n── {date_str} ──────────────────────────────")
    worst = "BIKE_CLEAR"
    for plz, graph in snapshot.items():
        result = decide(graph, date.fromisoformat(date_str))
        print(f"  PLZ {plz[:4]} … {result}")
        if SEVERITY[result] > SEVERITY[worst]:
            worst = result
    print(f"→ {DISPLAY[worst]}  (LCD_CODE={LCD_CODE[worst]})")


def main():
    if len(sys.argv) == 2:
        replay(sys.argv[1])
    else:
        dates = sorted(p.stem for p in SNAPSHOT_DIR.glob("*.json"))
        if not dates:
            print("No snapshots found. Run log_snapshot.py first.")
            return
        for d in dates:
            replay(d)


if __name__ == "__main__":
    main()
