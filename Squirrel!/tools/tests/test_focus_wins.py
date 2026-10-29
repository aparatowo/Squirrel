# tools/tests/test_focus_wins.py - taking focus time back (focus_timer.py), the success journal (success_log.py) and the
# watch's double / triple tap on the clock (screens/clock_screen.py) (CPython, from the folder with squirrel_app.py)
import os
import sys
import tempfile
import time
sys.path.insert(0, ".")
sys.path.append("tools/sim/fakes")                   # M5 (gfx); appended: their time / os stay CPython's
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


# ---- taking focus time back ----
from focus_timer import FocusTimer


class Rtc:
    def get_datetime(self):
        return (2026, 10, 19, 12, 0, 0, 0, 0)


base = tempfile.mkdtemp()
ft = FocusTimer(Rtc(), base + "/focus")
ft._use_day("2026-10-19")
ft._day_secs = 3600
ft._unsaved = {"2026-10-19": 3600}
ft._save()
check("an hour", ft.today_seconds() == 3600)
check("15 min back", ft.subtract(900) == 900 and ft.today_seconds() == 2700)
with open(base + "/focus/focus.txt") as f:
    check("a negative line", "2026-10-19,-900" in f.read())
ft2 = FocusTimer(Rtc(), base + "/focus")
check("read back after a restart", ft2.today_seconds() == 2700)
check("the week sees it", ft2.week(1)[0][2] == 2700)
check("never below zero", ft2.subtract(99999) == 2700 and ft2.today_seconds() == 0)
check("nothing left to take", ft2.subtract(900) == 0)
ft3 = FocusTimer(Rtc(), base + "/focus")
check("zero after a restart", ft3.today_seconds() == 0)
ft3._unsaved = {"2026-10-19": 600}
ft3._day_secs = 600
ft3._save()
check("reset_today", ft3.reset_today() == 600 and FocusTimer(Rtc(), base + "/focus").today_seconds() == 0)
ft4 = FocusTimer(Rtc(), base + "/focus")
check("start", ft4.start() == "started" and ft4.start() == "running" and ft4.state == "running")
check("halt", ft4.halt() == "paused" and ft4.halt() == "not_running" and ft4.state == "paused")
check("start resumes", ft4.start() == "resumed")

# ---- a restart while it runs: it goes on counting; the seconds wait for a date ----
check("running survives a restart", FocusTimer(Rtc(), base + "/focus").state == "running")
ft4.pause()
check("paused stays stopped after a restart", FocusTimer(Rtc(), base + "/focus").state == "stopped")
ft4.start()
ft4.stop()
check("stopped stays stopped after a restart", FocusTimer(Rtc(), base + "/focus").state == "stopped")


class NoDate:
    year = 2000

    def get_datetime(self):
        return (self.year, 1, 1, 0, 0, 0, 0, 0)


rtc = NoDate()
ft5 = FocusTimer(rtc, tempfile.mkdtemp() + "/focus")
ft5.start()
ft5._accumulate(ft5._last_ms + 5000)
check("no date: nothing counted yet", ft5._day_key is None and ft5._frac_ms == 5000)
rtc.year = 2026
ft5._accumulate(ft5._last_ms + 2000)
check("the date known: the waiting seconds go to it", ft5.today_seconds() == 7)

# ---- the success journal ----
import success_log
from success_log import SuccessLog, items, tidy
from storage_manager import StorageManager

check("items", items("2026-10-19\n- called mum\n> fixed the bike\ntired, but ok\n-\n  - ran 5 km") ==
      ["called mum", "fixed the bike", "ran 5 km"])
check("the date line is no item", items("- not an item\n- an item") == ["an item"])
check("tidy", tidy("2026-10-19", "2026-10-19\n- a\n- \n>\n\n") == "2026-10-19\n- a\n")
check("tidy puts the date first", tidy("2026-10-19", "- a").startswith("2026-10-19\n- a"))

st = StorageManager(tempfile.mkdtemp())
log = SuccessLog(st)
args = log.editor_args("2026-10-19")
check("a new day", args["file_index"] is None and args["body"] == "2026-10-19\n- " and args["day"] == "2026-10-19")
check("saved", log.save("2026-10-19", args["body"] + "called mum") and log.count("2026-10-19") == 1)
args = log.editor_args("2026-10-19")
check("the day again: its list and a new line", args["file_index"] == 0 and args["body"] == "2026-10-19\n- called mum\n- ")
log.save("2026-10-19", args["body"] + "fixed the bike")
check("two", log.count("2026-10-19") == 2 and st.stems("wins") == ["2026-10-19"])
log.save("2026-10-18", "2026-10-18\n> walked the dog")
check("another day", log.count("2026-10-18") == 1 and st.stems("wins") == ["2026-10-18", "2026-10-19"])
check("no file: 0", log.count("2026-01-01") == 0)

# ---- the watch's taps on the clock ----
import screens.clock_screen as cs


class Focus:
    def __init__(self):
        self.calls = []

    def start(self):
        self.calls.append("start")
        return "started"

    def halt(self):
        self.calls.append("halt")
        return "paused"


class App:
    def __init__(self):
        self.focus = Focus()
        self.keypad = type("K", (), {"touch": True})()
        self.screens_set = []
        self.rtc = type("R", (), {"get_time_str": staticmethod(lambda: "12:00")})()

    def set_screen(self, name, **kw):
        self.screens_set.append(name)


now = [0]
cs.time = type("T", (), {"ticks_ms": staticmethod(lambda: now[0]), "ticks_add": staticmethod(lambda a, b: a + b),
                         "ticks_diff": staticmethod(lambda a, b: a - b)})
app = App()
clock = cs.ClockScreen(app)
clock.on_enter()


def taps(n, gap=200):
    for i in range(n):
        clock.handle_input('ENTER')
        now[0] += gap
        clock.needs_refresh()                         # the main loop asks between the taps
    clock._shown_time = None
    now[0] += 1000
    clock._taps and clock.needs_refresh()


taps(1)
check("one tap: the menu", app.screens_set == ["MENU"] and app.focus.calls == [])
taps(2)
check("two taps: start", app.focus.calls == ["start"] and app.screens_set == ["MENU"])
taps(3)
check("three taps: pause", app.focus.calls == ["start", "halt"])
clock.handle_input('OPT')
check("a hold: nothing", len(app.focus.calls) == 2 and app.screens_set == ["MENU"])
check("no waking hook: the app swallows the waking tap", not hasattr(clock, "on_waking_action"))
taps(2, gap=600)
check("too slow: two single taps", app.screens_set == ["MENU", "MENU", "MENU"] and len(app.focus.calls) == 2)

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
