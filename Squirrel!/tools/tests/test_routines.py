# tools/tests/test_routines.py - routines.json with ids, the device filter and the routine log (CPython)
import json
import os
import sys
import tempfile
sys.path.insert(0, ".")
import time
if not hasattr(time, "ticks_ms"):                # CPython: MicroPython's tick counters
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_add = lambda a, b: a + b
    time.ticks_diff = lambda a, b: a - b
import types
_n = types.ModuleType("notifier")               # the real one draws on the display


class _Notification:
    def __init__(self, text, **kw):
        self.text = text
        self.__dict__.update(kw)


_n.Notification = _Notification
sys.modules["notifier"] = _n
import scheduler
from scheduler import RoutineStore, EventLog

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


d = tempfile.mkdtemp()
path = d + "/routines.json"
with open(path, "w") as f:                       # a file of version 1.x
    f.write('[{"t": "Leki", "h": 8, "m": 0, "on": true, "d": 63}, {"t": "Daily", "h": 10, "m": 21, "on": true, "d": 31}]')
st = RoutineStore(path)
check("ids given", [r["id"] for r in st.items] == [1, 2])
check("defaults", st.items[0]["to"] == 255 and st.items[0]["e"] == 0 and st.items[0]["c"] == 0)
check("written back", [r["id"] for r in json.load(open(path))] == [1, 2])
check("same ids on reload", [r["id"] for r in RoutineStore(path).items] == [1, 2])

r = st.create()
check("new id", r["id"] == 3 and r["e"] > 0 and r in st.items)
RoutineStore.state_changed(r)
check("state time", r["c"] > 0)

watch = RoutineStore(path, slot=1)
only_head = dict(st.items[0], to=0b01)
check("filter: head", st.comes_up(only_head, 0))
check("filter: not on the watch", not watch.comes_up(only_head, 0))
check("filter: all", watch.comes_up(dict(only_head, to=255), 0))
check("filter: day", not st.comes_up(only_head, 6))           # d = 63: not on Sunday

# the log
log_path = d + "/focus/events.txt"
ev = EventLog(log_path, keep_s=100)
ev.add(1, 1000, "done")
ev.add(2, 1050, "skip")
ev.add(1, 1100, "missed")
check("since", ev.since(1000) == [{"r": 2, "at": 1050, "res": "skip"}, {"r": 1, "at": 1100, "res": "missed"}])
check("trim", ev.trim(1120) == 1 and [e["at"] for e in ev.since()] == [1050, 1100])

# the scheduler records what became of a routine
fired = []


class Notifier:
    def post(self, n):
        fired.append(n)


class Cfg:
    def get(self, k):
        return 10 if k == "ROUTINE_SNOOZE_MIN" else False


class Counter:
    def add(self, *a):
        pass


ev2 = EventLog(d + "/ev2.txt")
s = scheduler.Scheduler(st, Notifier(), None, Cfg(), Counter(), events=ev2)
s._fire(st.items[0], 0, 5000)
fired[-1].on_done()
s._fire(st.items[1], 0, 6000)
fired[-1].on_cancel()
scheduler.nuts.ROUTINE_MAX_SNOOZES = 1
s._fire(st.items[0], 1, 7000)
fired[-1].on_timeout()
check("log of outcomes", ev2.since() == [{"r": 1, "at": 5000, "res": "done"}, {"r": 2, "at": 6000, "res": "skip"},
                                         {"r": 1, "at": 7000, "res": "missed"}])
s._fire(st.items[0], 0, 8000)
fired[-1].on_timeout()
check("snooze keeps the time", s._snoozed[-1][4] == 8000 and s.export_snoozes()[-1][3] == 8000)
s2 = scheduler.Scheduler(st, Notifier(), None, Cfg(), Counter(), events=ev2)
s2.import_snoozes([[0, st.items[0], 1]])                       # saved by version 1.x
check("old snoozes", s2._snoozed[0][4] == 0)

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
