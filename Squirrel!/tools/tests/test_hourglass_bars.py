# tools/tests/test_hourglass_bars.py - the hourglass (hourglass.py) and the clock's bars (bars.py): the time bars at the
# top and bottom, the focus bar rising from the bottom (CPython, from the folder with squirrel_app.py)
import sys
import time
sys.path.insert(0, ".")
sys.path.append("tools/sim/fakes")                   # M5 (notifier -> gfx); appended: their time / os stay CPython's
if not hasattr(time, "ticks_ms"):                     # MicroPython's tick functions, for CPython
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b

from bars import StatusBars, time_cells
from hourglass import Hourglass

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


class Clock:
    ms = 0

    def __call__(self):
        return self.ms


class Notifier:
    def __init__(self):
        self.posted = []

    def post(self, n):
        self.posted.append(n)


# ---- the hourglass ----
clock = Clock()
notifier = Notifier()
hg = Hourglass(notifier, now_ms=clock)
check("idle", hg.state == "idle" and hg.remaining() == 0 and hg.elapsed_ms() == 0)
hg.start(90)
clock.ms = 30_000
hg.tick()
check("running", hg.state == "running" and hg.remaining() == 60 and hg.elapsed_ms() == 30_000)
hg.toggle()
clock.ms = 100_000                                    # paused: the time does not count
check("paused", hg.state == "paused" and hg.remaining() == 60)
hg.toggle()
clock.ms = 159_500
hg.tick()
check("half a second left", hg.state == "running" and hg.remaining() == 1)
clock.ms = 160_000
hg.tick()
check("done", hg.state == "done" and hg.remaining() == 0 and hg.elapsed_ms() == 90_000)
check("rings once", len(notifier.posted) == 1)
n = notifier.posted[0]
check("alarm signals", n.sound == "alarm" and n.force and n.buzzer[0] == "BUZZER_HOURGLASS" and n.led == "LED_HOURGLASS")
hg.tick()
check("still once", len(notifier.posted) == 1)
n.on_done()
check("answered: idle", hg.state == "idle")

# ---- time cells ----
check("half", time_cells(30, 60, 6, "g") == ["g", "g", "g", None, None, None])
check("from the right", time_cells(15, 60, 4, "g", from_right=True) == [None, None, None, "g"])
check("full only at the end", time_cells(59, 60, 4, "g") == ["g", "g", "g", None] and time_cells(60, 60, 4, "g") == ["g"] * 4)
check("blink on", time_cells(0, 60, 3, "g", blink_on=True) == ["g", None, None])
check("blink off", time_cells(40, 60, 3, "g", blink_on=False) == ["g", None, None])

# ---- the bars ----


class Cfg(dict):
    def get(self, key):
        return self[key]


class Focus:
    state = "stopped"
    goal_seconds = 100

    def today_seconds(self):
        return 50


cfg = Cfg(BARS_TOP="hourglass", BARS_TOP_COLOR="green", BARS_BOTTOM="quarter", BARS_BOTTOM_COLOR="cyan",
          FOCUS_BAR_FROM="bottom", FOCUS_RED_PCT=25, FOCUS_YELLOW_PCT=60)
now = [(2026, 10, 18, 14, 30, 0, 6, 0)]
current = [None]
bars = StatusBars(cfg, None, Focus(), now_ms=lambda: 0, clock=lambda: now[0], hourglass=lambda: current[0])

check("hour, half gone", bars.top_cells(4) == ["green", "green", None, None])
check("quarter just started", bars.bottom_cells(4) == [None] * 4)
now[0] = (2026, 10, 18, 14, 37, 30, 6, 0)            # half of the quarter 14:30-14:45
check("quarter, half gone", bars.bottom_cells(4) == [None, None, "cyan", "cyan"])
now[0] = (2026, 10, 18, 14, 45, 0, 6, 0)
check("next quarter starts empty", bars.bottom_cells(4) == [None] * 4)

clock.ms = 0
current[0] = hg
hg.start(100)
clock.ms = 50_000
check("hourglass half gone, blinking", bars.top_cells(4) == ["green", "green", None, None])
hg.toggle()
check("paused: no blink", bars.top_cells(4) == ["green", "green", None, None])
bars._now = lambda: 500
hg.toggle()
check("running, blink off", bars.top_cells(4) == ["green", None, None, None])
hg.stop()
check("idle: the hour again", bars.top_cells(4) == ["green", "green", "green", None])     # 14:45

cfg["BARS_TOP"] = "hour"
hg.start(100)
check("hour mode ignores the hourglass", bars.top_cells(4) == ["green", "green", "green", None])
cfg["BARS_TOP"], cfg["BARS_BOTTOM"] = "full", "full"
check("full", bars.top_cells(3) == [None] * 3 and bars.bottom_cells(3) == [None] * 3)
cfg["BARS_TOP"], cfg["BARS_BOTTOM"] = "off", "off"
check("off", bars.top_cells(3) is None and bars.bottom_cells(3) is None)

check("focus rises from the bottom", bars.focus_cells(4, vertical=True) == [None, None, "yellow", "yellow"])
check("the menu bar is unchanged", bars.focus_cells(4) == ["yellow", "yellow", None, None])
cfg["FOCUS_BAR_FROM"] = "top"
check("classic: from the top", bars.focus_cells(4, vertical=True) == ["yellow", "yellow", None, None])

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
