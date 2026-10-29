# tools/tests/test_wifi.py - which WiFi networks are tried, in which order (wifi_profiles.plan_networks), the old single
# fallback joining the saved networks (adopt_fallback), and the time sync trying them one after another (time_sync.py)
# (CPython, from the folder with squirrel_app.py)
import os
import sys
import tempfile
import time
sys.path.insert(0, ".")
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b

from wifi_profiles import plan_networks, adopt_fallback, WifiProfiles

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


scan = [(b"Home WiFi", b"x", 6, -70, 3, 0), (b"Neighbour", b"y", 1, -40, 3, 0), (b"Office", b"z", 11, -55, 3, 0),
        (b"Home WiFi", b"x2", 6, -60, 3, 0), (b"", b"h", 3, -50, 3, 1)]
known = [("home wifi ", "p1", "saved"), ("Cafe", "p2", "saved"), ("Office", "p3", "saved")]
order = plan_networks(scan, known)
check("in range first, strongest first", [o[0] for o in order] == ["Office", "Home WiFi", "Cafe"])
check("the scan's spelling, the best signal", order[1] == ("Home WiFi", "p1", "saved", -60))
check("unseen last, without rssi", order[2] == ("Cafe", "p2", "saved", None))
check("a space typed inside the name", plan_networks([(b"Home_5G", b"q", 11, -30, 3, 0)], [("Home _5G", "p", "saved")])
      == [("Home_5G", "p", "saved", -30)])
check("nothing in range: all, in their order", [o[0] for o in plan_networks([], known)] == ["home wifi ", "Cafe", "Office"])


class Cfg(dict):
    def get(self, key):
        return self[key]

    def set(self, key, value, save=True):
        self[key] = value


path = os.path.join(tempfile.mkdtemp(), "wifi.json")
cfg = Cfg(WIFI_SSID="Cafe", WIFI_PASSWORD="secret")
check("the fallback moves", adopt_fallback(cfg, path) and WifiProfiles(path).all() == [("Cafe", "secret")])
check("... and is cleared", cfg["WIFI_SSID"] == "" and cfg["WIFI_PASSWORD"] == "")
check("nothing to move", adopt_fallback(cfg, path) is False)

from time_sync import TimeSyncService


class Net:
    """Networks that answer: their names; the others fail."""
    def __init__(self, plan, good):
        self._plan, self._good, self.tried, self.closed = plan, good, [], False
        self._now = None

    def plan(self):
        return list(self._plan)

    def begin(self, ssid, pswd):
        self.tried.append(ssid)
        self._now = ssid

    def poll(self):
        return "connected" if self._now in self._good else "failed: network not found"

    def query_utc(self, attempt=0):
        return (2026, 10, 19, 16, 0, 0)

    def close(self):
        self.closed = True


class Rtc:
    last_sync_source = "soft"

    def set_manual(self, dt):
        self.dt = dt


net = Net([("A", "", "saved", -50), ("B", "", "saved", -60), ("C", "", "saved", None)], good={"C"})
rtc = Rtc()
ts = TimeSyncService(rtc, net, utc_offset_min=60, eu_dst=False)
ts.start("test")
for _ in range(10):
    ts.tick()
check("one after another", net.tried == ["A", "B", "C"] and ts.state == "done" and rtc.dt[3] == 17)
net = Net([("A", "", "saved", -50)], good=set())
ts = TimeSyncService(Rtc(), net)
ts.start("test")
for _ in range(5):
    ts.tick()
check("all failed: the last problem", ts.state == "failed" and ts.message == "network not found" and net.closed)

class BadPass(Net):
    def poll(self):
        return "failed: wrong password" if self._now == "A" else "failed: network not found"


net = BadPass([("A", "", "saved", -40), ("B", "", "saved", None)], good=set())
ts = TimeSyncService(Rtc(), net)
ts.start("test")
for _ in range(5):
    ts.tick()
check("the in-range network's problem is the one shown", net.tried == ["A", "B"] and ts.message == "wrong password")

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
