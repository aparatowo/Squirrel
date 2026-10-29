# tools/tests/test_metronome.py - the metronome (intervals.py): every beat the same sound, on time to the millisecond
# (a beat due before the main loop comes round again is waited for), and its click (sound.py)
# (CPython, from the folder with squirrel_app.py)
import sys
import time
sys.path.insert(0, ".")
sys.path.append("tools/sim/fakes")
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b
    time.sleep_ms = lambda ms: None

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


import intervals
import sound


class Audio:
    def __init__(self):
        self.played = []

    def is_recording(self):
        return False

    def beep(self, pattern, **k):
        self.played.append((clock[0], pattern))


class Cfg(dict):
    def get(self, key):
        return self[key]


clock = [0]
slept = []


def sleep(ms):
    slept.append(ms)
    clock[0] += ms


audio = Audio()
cfg = Cfg(METRO_INTERVAL_S=0.5, METRO_VOLUME=50, METRO_SOUND="tone")
m = intervals.Metronome(audio, cfg, now_ms=lambda: clock[0], sleep_ms=sleep)
m.start()
for _ in range(200):                       # the main loop: a tick every 23 ms (20 ms pause + its work)
    m.tick()
    clock[0] += 23
times = [t for t, _p in audio.played]
gaps = [b - a for a, b in zip(times, times[1:])]
check("beats on time", gaps and all(g == 500 for g in gaps))
check("waited for, never a loop late", slept and max(slept) <= intervals._ON_TIME_MS)
check("every beat the same", set(p for _t, p in audio.played) == {"tick"})
cfg["METRO_SOUND"] = "click"
m.tick()
clock[0] += 500
m.tick()
check("the click", audio.played[-1][1] == "click")
pcm = sound.build("click")
first = int.from_bytes(pcm[0:2], "little", signed=True)
last = int.from_bytes(pcm[-2:], "little", signed=True)
check("a click: one push that dies away", first > 0 and 0 <= last < first // 4 and len(pcm) == 2 * 24)

print("FAILED: %s" % ", ".join(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
