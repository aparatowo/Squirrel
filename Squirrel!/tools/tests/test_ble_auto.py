# tools/tests/test_ble_auto.py - ble/auto.py: the slots on the clock, the watch's wake-ups, when a session starts
import sys
import time
sys.path.insert(0, ".")
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_add = lambda a, b: a + b
    time.ticks_diff = lambda a, b: a - b
from ble import auto as A

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


class Cfg:
    def __init__(self, minutes):
        self.minutes = minutes

    def get(self, key):
        assert key == "BLE_AUTO_SYNC_MIN"
        return self.minutes


class Radio:
    ble_in_use = False


class App:
    def __init__(self):
        self.radio = Radio()
        self.wifi = False

    def _radio_in_use(self):
        return self.wifi


def at(h, m, s=0):
    return time.mktime((2026, 10, 13, h, m, s, 0, 0, -1))


now = [at(10, 0)]
A.time.time = lambda: now[0]

check("slot of 10:07 every 30", A.slot_of(at(10, 7), 1800) == at(10, 0))
check("slot of 10:31 every 30", A.slot_of(at(10, 31), 1800) == at(10, 30))
check("slot of 23:59 every 45", A.slot_of(at(23, 59), 2700) == at(23, 15))

# the watch: wake-ups at the coming slots
node = A.AutoSync(App(), Cfg(60), "node")
ev = node.events(at(10, 5), at(13, 0))
check("node wakes at full hours", [e[0] for e in ev] == [at(11, 0), at(12, 0), at(13, 0)])
check("head is no alarm source", A.AutoSync(App(), Cfg(60), "head").events(at(10, 5), at(13, 0)) == [])
check("off: no wake-ups", A.AutoSync(App(), Cfg(0), "node").events(at(10, 5), at(13, 0)) == [])

# when a session starts
started = []


def make(role, minutes=60, app=None):
    s = A.AutoSync(app or App(), Cfg(minutes), role)
    s._start_head = lambda: started.append(("head", now[0]))
    s._start_node = lambda window: started.append(("node", now[0], int(window)))
    return s


def tick(s, t):
    now[0] = t
    s._checked = -10 ** 9
    s.tick()


head, watch = make("head"), make("node")
for t in (at(10, 59, 50), at(11, 0, 0), at(11, 0, 5), at(11, 0, 20), at(11, 0, 30)):
    tick(head, t)
    tick(watch, t)
check("node starts at the slot, for the window", ("node", at(11, 0), A.NODE_WINDOW_S) in started)
check("head starts HEAD_DELAY_S later", ("head", at(11, 0, A.HEAD_DELAY_S)) in started)
check("each once per slot", len(started) == 2)

started.clear()
late = make("node")
tick(late, at(11, 0, 40))                                 # a slow wake-up: still taken, with what is left of it
check("late node: the rest of the window", started == [("node", at(11, 0, 40), A.NODE_WINDOW_S - 40)])
started.clear()
tick(make("node"), at(11, 5))
check("too late: skipped", started == [])

busy_app = App()
busy_app.radio.ble_in_use = True
tick(make("head", app=busy_app), at(12, 0, 25))
busy_app.radio.ble_in_use = False
busy_app.wifi = True
tick(make("head", app=busy_app), at(12, 0, 25))
check("radio taken: skipped", started == [])
tick(make("head", minutes=0), at(12, 0, 25))
check("off: never", started == [])

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
