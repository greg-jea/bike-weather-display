"""
bike-weather-display — weather checker
Uses the MeteoSwiss app API (the backend of the MeteoSwiss mobile app; undocumented, may change).
Decides: TRAIN | BIKE_WET | BIKE_CLEAR
"""

import sys
from datetime import date, datetime, timezone
import requests

# ── Locations ─────────────────────────────────────────────────────────────────
# MeteoSwiss format: 4-digit PLZ + "00"
# All zones along the route are checked; worst-case result wins.
# Your postal codes live in config.py (git-ignored) — copy config.example.py to start.
try:
    from config import PLZS
except ImportError:
    sys.exit("config.py missing — run: cp config.example.py config.py")

# ── Decision thresholds ───────────────────────────────────────────────────────
RAIN_DAY_START    = 6     # 06:00 — start of "would I cycle today?" window
RAIN_DAY_END      = 18    # 18:00
WET_ROAD_CUTOFF   = 7     # roads considered wet if it rained before 07:00
RAIN_THRESHOLD_MM = 0.1   # mm per interval to count as rain

# ── MeteoSwiss API ────────────────────────────────────────────────────────────
METEOSWISS_URL = "https://app-prod-ws.meteoswiss-app.ch/v1/plzDetail"


def fetch(plz: str) -> dict:
    resp = requests.get(METEOSWISS_URL, params={"plz": plz}, timeout=10)
    resp.raise_for_status()
    return resp.json()["graph"]


def to_local_dt(ms: int) -> datetime:
    """Unix ms → datetime in the system's local time zone (set the Pi to Europe/Zurich)."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()


def decide(graph: dict, day: date = None) -> str:
    """Decide for `day` (default: today). Replays pass the snapshot's date."""
    day = day or datetime.now().astimezone().date()

    start_10m = graph["start"]            # ms, start of 10-min actual data
    start_1h  = graph["startLowResolution"]  # ms, start of 1-h forecast data

    precip_10m = graph["precipitation10m"]   # measured: past hours in 10-min slots
    precip_1h  = graph["precipitation1h"]    # forecast: coming hours in 1-h slots

    # ── 1. Any rain measured or forecast between 06:00 and 18:00 today? → TRAIN ─
    # Check 10-min measured data (catches currently-raining situations)
    for i, mm in enumerate(precip_10m):
        slot_ms = start_10m + i * 600_000
        dt = to_local_dt(slot_ms)
        if dt.date() != day:
            continue
        if RAIN_DAY_START <= dt.hour < RAIN_DAY_END and mm >= RAIN_THRESHOLD_MM:
            return "TRAIN"

    # Check 1h forecast for upcoming rain during day
    for i, mm in enumerate(precip_1h):
        slot_ms = start_1h + i * 3_600_000
        dt = to_local_dt(slot_ms)
        if dt.date() != day:
            continue
        if RAIN_DAY_START <= dt.hour < RAIN_DAY_END and mm >= RAIN_THRESHOLD_MM:
            return "TRAIN"

    # ── 2. Did it rain before 07:00 today? (roads still wet) → BIKE_WET ───────
    # Check 10-min measured data (covers midnight → now)
    for i, mm in enumerate(precip_10m):
        slot_ms = start_10m + i * 600_000
        dt = to_local_dt(slot_ms)
        if dt.date() != day:
            continue
        if dt.hour < WET_ROAD_CUTOFF and mm >= RAIN_THRESHOLD_MM:
            return "BIKE_WET"

    # Also check early 1h forecast slots before the cutoff
    for i, mm in enumerate(precip_1h):
        slot_ms = start_1h + i * 3_600_000
        dt = to_local_dt(slot_ms)
        if dt.date() != day:
            continue
        if dt.hour < WET_ROAD_CUTOFF and mm >= RAIN_THRESHOLD_MM:
            return "BIKE_WET"

    # ── 3. All clear ──────────────────────────────────────────────────────────
    return "BIKE_CLEAR"


DISPLAY = {
    "TRAIN":      "TAKE TRAIN  (rain expected between 06:00-18:00)",
    "BIKE_WET":   "TAKE BIKE   (roads still wet — watch out)",
    "BIKE_CLEAR": "TAKE BIKE   (all clear, enjoy the ride!)",
}

LCD_CODE = {"TRAIN": 0, "BIKE_WET": 1, "BIKE_CLEAR": 2}


SEVERITY = {"TRAIN": 2, "BIKE_WET": 1, "BIKE_CLEAR": 0}


def main():
    worst = "BIKE_CLEAR"
    for plz in PLZS:
        print(f"  PLZ {plz[:4]} …", end=" ")
        try:
            graph = fetch(plz)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                print("not in MeteoSwiss coverage, skipped")
                continue
            print(f"HTTP error: {e}", file=sys.stderr)
            sys.exit(1)
        except requests.RequestException as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
        result = decide(graph)
        print(result)
        if SEVERITY[result] > SEVERITY[worst]:
            worst = result

    print(f"\n→ {DISPLAY[worst]}")
    print(f"LCD_CODE={LCD_CODE[worst]}")
    return LCD_CODE[worst]


if __name__ == "__main__":
    main()
