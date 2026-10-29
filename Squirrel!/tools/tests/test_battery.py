# tools/tests/test_battery.py - charging guessed from the voltage (hw/battery.py), the low-battery warnings
# (battery_alerts.py) with their LED signal, and the charging mark (bars.py) (CPython, from the folder with squirrel_app.py)
import sys
import time
sys.path.insert(0, ".")
sys.path.append("tools/sim/fakes")                   # M5 (notifier -> gfx); appended: their time / os stay CPython's
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b

from hw.battery import ChargeGuess, BatteryMonitor
from battery_alerts import BatteryAlerts

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


# ---- the guess ----
g = ChargeGuess()
check("on battery at start", g.feed(3900) is False)
for mv in (3898, 3897, 3897):
    g.feed(mv)
check("a jump alone is not enough", g.feed(4010) is False)
check("the jump stays: plugged in", g.feed(4015) is True)
g.feed(4020)
check("a radio's dip does not unplug", g.feed(3950) is True and g.feed(4022) is True)
g.feed(3930)
check("the drop stays: unplugged", g.feed(3925) is False)

g = ChargeGuess()
check("above 4.2 V at start: on a charger", g.feed(4205) is True)

g = ChargeGuess()
mv = 4100
for _ in range(ChargeGuess.WINDOW):                  # a nearly full battery: a slow rise, no jump
    g.feed(mv)
    mv += 1
check("a slow rise: charging", g.charging is True)
for _ in range(ChargeGuess.WINDOW):
    g.feed(mv)
    mv -= 1
check("a slow fall: not charging", g.charging is False)

g = ChargeGuess()
g.feed(3800)
check("a computer's frames: charging", g.feed(3801, usb=True) is True)

# ---- the monitor ----
guessing = [False]
mon = BatteryMonitor(read=lambda: 50, charging=lambda: None, millivolts=lambda: 3900, guess=lambda: guessing[0])
check("unknown without the guess", mon.charging is None and not mon.charging_guessed and mon.millivolts == 3900)
guessing[0] = True
mon._poll()
check("the guess when on", mon.charging is False and mon.charging_guessed)
mon2 = BatteryMonitor(read=lambda: 50, charging=lambda: True, guess=lambda: True)
check("a device that tells is not guessed", mon2.charging is True and not mon2.charging_guessed)

# ---- the warnings ----


class Cfg(dict):
    def get(self, key):
        return self[key]


class Notifier:
    def __init__(self):
        self.posted = []

    def post(self, n):
        self.posted.append(n)


class Monitor:
    level_pct = 50
    charging = False
    millivolts = 3800


cfg = Cfg(BATTERY_WARN=True, BATTERY_WARN_SOUND=True)
clock = [0]
m, n = Monitor(), Notifier()
alerts = BatteryAlerts(cfg, m, n, now_ms=lambda: clock[0])


def at(level, mv=3800, charging=False):
    m.level_pct, m.millivolts, m.charging = level, mv, charging
    clock[0] += 10000
    alerts.tick()
    return len(n.posted)


check("50%: nothing", at(50) == 0)
check("15%", at(15) == 1 and "15" in n.posted[-1].text)
check("14%: not again", at(14) == 1)
check("16%: wobbles back", at(16) == 1)
check("15% again: no (within 3)", at(15) == 1)
check("10%", at(10) == 2)
check("the buzzer, double", n.posted[-1].buzzer == ("BUZZER_BATTERY", "double") and n.posted[-1].sound == "battery")
check("13%: 10 counts again", at(13) == 2)
check("10% again: once more", at(10) == 3)
check("5%", at(5) == 4)
check("2%: almost empty", at(2) == 5 and n.posted[-1].buzzer[1] == "alarm")
check("1%: no more", at(1) == 5)
check("charging forgets", at(1, charging=True) == 5 and at(20) == 5)
check("after a charge: 15% again", at(15) == 6)
check("a low voltage is almost empty too", at(12, mv=3390) == 7 and n.posted[-1].buzzer[1] == "alarm")
n2 = Notifier()
a2 = BatteryAlerts(cfg, m, n2, now_ms=lambda: clock[0])
m.level_pct, m.millivolts, m.charging = 7, 3700, False
clock[0] += 10000
a2.tick()
check("switched on at 7%: only the lowest crossed", len(n2.posted) == 1 and "7" in n2.posted[0].text)
cfg["BATTERY_WARN_SOUND"] = False
cfg["BATTERY_WARN"] = True
a3 = BatteryAlerts(cfg, m, n2, now_ms=lambda: clock[0])
clock[0] += 10000
a3.tick()
check("no sound when it is off", n2.posted[-1].sound is None)
cfg["BATTERY_WARN"] = False
a4 = BatteryAlerts(cfg, m, n2, now_ms=lambda: clock[0])
clock[0] += 10000
a4.tick()
check("off: quiet", len(n2.posted) == 2)

# ---- the LED and the charging mark ----
import hw.led as L
check("the warnings may light the LED", "LED_BATTERY" in L.FEATURES)
check("a warning blinks the LED", n.posted[0].led == "LED_BATTERY")
from bars import StatusBars
bat = Monitor()
marks = Cfg(BARS_CHARGING=True)
sb = StatusBars(marks, bat, None)
bat.charging = True
check("charging: the mark", sb.charging())
bat.charging = None
check("unknown: no mark", not sb.charging())
bat.charging = True
marks["BARS_CHARGING"] = False
check("switched off: no mark", not sb.charging())

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
