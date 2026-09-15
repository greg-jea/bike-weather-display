"""
Display driver — shows the weather decision on the ST7735S LCD (128×160).

Usage:
    python3 display.py              # check weather, update display
    python3 display.py 0|1|2        # force result for testing (0=TRAIN 1=WET 2=CLEAR)
    python3 display.py --off        # turn backlight off
"""

import sys
from datetime import datetime
from pathlib import Path
from PIL import Image

from weather_checker import PLZS, fetch, decide, SEVERITY, DISPLAY, LCD_CODE

W, H = 128, 160

BL_PIN = 18          # GPIO 18 · Pin 12 — backlight control
NIGHT_START = 19     # 19:00 — backlight off
NIGHT_END   = 6      # 06:00 — backlight on

# TODO: physical button (future feature)
# A button connected to a GPIO pin should, when pressed during night hours (19:00–06:00):
#   1. Turn the backlight on and show the current weather result for 10 seconds
#   2. Then turn the backlight off again
#   3. UNLESS the clock has passed 06:00 while the display was on — in that case leave it on
# Implementation note: use a GPIO interrupt (edge detection) on the button pin so it works
# even while the Pi is idle between cron runs. A background service/daemon will be needed
# (e.g. a small script run at @reboot that loops waiting for the button press).

# ── Screens ───────────────────────────────────────────────────────────────────
# One image per result, shared with the README. They are stored at 3× size so they
# stay sharp on GitHub, and scaled back down to the panel resolution here.
SCREEN_DIR = Path(__file__).resolve().parent.parent / "images"


def load_screen(result: str) -> Image.Image:
    img = Image.open(SCREEN_DIR / f"preview_{result.lower()}.png").convert("RGB")
    return img.resize((W, H), Image.NEAREST)


# ── Backlight ─────────────────────────────────────────────────────────────────

def backlight(on: bool):
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BL_PIN, GPIO.OUT)
    GPIO.output(BL_PIN, GPIO.HIGH if on else GPIO.LOW)


def is_night() -> bool:
    h = datetime.now().hour
    return h >= NIGHT_START or h < NIGHT_END


# ── Hardware ──────────────────────────────────────────────────────────────────

def get_device():
    import board
    import digitalio
    import adafruit_rgb_display.st7735 as st7735
    cs  = digitalio.DigitalInOut(board.CE0)
    dc  = digitalio.DigitalInOut(board.D24)
    rst = digitalio.DigitalInOut(board.D25)
    spi = board.SPI()
    # The panel's visible area starts 2 columns / 1 row into its memory. Without the
    # offset, the image is shifted and a noise strip shows on the right and bottom edge.
    return st7735.ST7735R(spi, cs=cs, dc=dc, rst=rst, width=W, height=H, rotation=0, bgr=True,
                          x_offset=2, y_offset=1)


# ── Weather check ─────────────────────────────────────────────────────────────

def run_weather() -> str:
    worst = "BIKE_CLEAR"
    for plz in PLZS:
        try:
            graph = fetch(plz)
        except Exception:
            continue
        result = decide(graph)
        if SEVERITY[result] > SEVERITY[worst]:
            worst = result
    return worst


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if "--off" in args:
        backlight(False)
        print("Backlight off")
        return

    if is_night():
        backlight(False)
        print("Night hours — backlight off")
        return

    if args and args[0] in ("0", "1", "2"):
        result = {0: "TRAIN", 1: "BIKE_WET", 2: "BIKE_CLEAR"}[int(args[0])]
        print(f"Forced: {result}")
    else:
        result = run_weather()
        print(f"→ {DISPLAY[result]}  (LCD_CODE={LCD_CODE[result]})")

    backlight(True)
    img = load_screen(result)
    device = get_device()
    device.image(img)


if __name__ == "__main__":
    main()
