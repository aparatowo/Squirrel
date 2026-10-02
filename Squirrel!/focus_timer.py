# focus_timer.py - focus time counter that runs in the background
#
# States: 'stopped' (idle) -> 'running' <-> 'paused'.  Time is counted from
# time.ticks_ms(), so it does not depend on the RTC being right; the RTC only
# decides which calendar day the counted seconds belong to.  Totals per day are
# kept in <data_dir>/focus.txt as "YYYY-MM-DD,seconds" lines and written at most
# every 15 minutes while running, and on every pause / stop.

import os
import time
from boot_log import log
from timeutil import days_from_civil, civil_from_days, weekday_from_days

_SAVE_INTERVAL_MS = 15 * 60 * 1000
_MIN_VALID_YEAR = 2024        # anything earlier means the clock was never set


def _key(y, m, d):
    return "%04d-%02d-%02d" % (y, m, d)


class FocusTimer:
    def __init__(self, rtc, data_dir, goal_seconds=6 * 3600):
        self._rtc = rtc
        self._dir = data_dir
        self._file = data_dir + "/focus.txt"
        self._tmp = data_dir + "/focus.tmp"
        self._goal = goal_seconds      # a number, or a function returning it (read live)
        self.state = "stopped"
        self._days = {}              # "YYYY-MM-DD" -> seconds
        self._last_ms = 0
        self._frac_ms = 0
        self._last_save_ms = 0
        self._last_key = None
        self._dirty = False
        self._load()

    @property
    def goal_seconds(self):
        goal = self._goal
        return goal() if callable(goal) else goal

    # ---------------- control ----------------

    def toggle(self):
        """Start / pause / resume.  Returns 'started', 'resumed', 'paused' or 'no_time'."""
        if self.state == "running":
            self.pause()
            return "paused"
        if self._today_key() is None:
            return "no_time"                 # would file the time under a bogus date
        was_paused = (self.state == "paused")
        now = time.ticks_ms()
        self.state = "running"
        self._last_ms = now
        self._frac_ms = 0
        self._last_save_ms = now
        return "resumed" if was_paused else "started"

    def pause(self):
        if self.state == "running":
            self._accumulate(time.ticks_ms())
            self.state = "paused"
            self._save()

    def stop(self):
        if self.state == "running":
            self._accumulate(time.ticks_ms())
        if self.state != "stopped":
            self.state = "stopped"
            self._save()

    # ---------------- service tick ----------------

    def tick(self):
        if self.state != "running":
            return
        now = time.ticks_ms()
        self._accumulate(now)
        if self._dirty and time.ticks_diff(now, self._last_save_ms) >= _SAVE_INTERVAL_MS:
            self._save()

    def _accumulate(self, now):
        self._frac_ms += time.ticks_diff(now, self._last_ms)
        self._last_ms = now
        seconds = self._frac_ms // 1000
        if seconds <= 0:
            return
        self._frac_ms -= seconds * 1000
        key = self._today_key() or self._last_key    # keep counting if the clock is being edited
        if key is None:
            return
        self._last_key = key
        self._days[key] = self._days.get(key, 0) + seconds
        self._dirty = True

    # ---------------- queries ----------------

    def indicator(self):
        return self.state

    def today_seconds(self):
        key = self._today_key()
        return self._days.get(key, 0) if key else 0

    def goal_reached(self):
        return self.today_seconds() >= self.goal_seconds

    def week(self, n=7):
        """Last n days, oldest first, ending today: [(date_key, weekday 0=Mon, seconds)]."""
        key = self._today_key()
        if key is None:
            return []
        base = days_from_civil(int(key[0:4]), int(key[5:7]), int(key[8:10]))
        result = []
        for back in range(n - 1, -1, -1):
            z = base - back
            y, m, d = civil_from_days(z)
            k = _key(y, m, d)
            result.append((k, weekday_from_days(z), self._days.get(k, 0)))
        return result

    def _today_key(self):
        """'YYYY-MM-DD' from the RTC, or None while the clock is unset / implausible."""
        try:
            dt = self._rtc.get_datetime()
            y, m, d = dt[0], dt[1], dt[2]
        except Exception:
            return None
        if y < _MIN_VALID_YEAR or not 1 <= m <= 12 or not 1 <= d <= 31:
            return None
        return _key(y, m, d)

    # ---------------- persistence ----------------

    def _load(self):
        for path in (self._file, self._tmp):     # tmp only survives an interrupted save
            try:
                with open(path, "r") as f:
                    text = f.read()
            except OSError:
                continue
            bad = 0
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    key, secs = line.split(",")
                    secs = int(secs)
                    if len(key) != 10 or key[4] != "-" or key[7] != "-" or secs < 0:
                        raise ValueError
                    int(key[0:4]); int(key[5:7]); int(key[8:10])
                    self._days[key] = secs
                except Exception:
                    bad += 1
            log(f"[FOCUS] Loaded {len(self._days)} day(s) from {path}" + (f" ({bad} bad line(s) skipped)" if bad else ""))
            return

    def _ensure_dir(self):
        try:
            os.stat(self._dir)
            return True
        except OSError:
            pass
        try:
            os.mkdir(self._dir)
            return True
        except Exception as e:
            log(f"[FOCUS] Cannot create {self._dir}: {e}")
            return False

    def _save(self):
        """Write all totals; FAT cannot rename over an existing file, so: tmp, remove, rename."""
        if not self._ensure_dir():
            return False
        try:
            with open(self._tmp, "w") as f:
                for key in sorted(self._days):
                    f.write("%s,%d\n" % (key, self._days[key]))
            try:
                os.remove(self._file)
            except OSError:
                pass
            os.rename(self._tmp, self._file)
            self._dirty = False
            self._last_save_ms = time.ticks_ms()
            return True
        except Exception as e:
            log(f"[FOCUS] Save failed: {e}")
            self._last_save_ms = time.ticks_ms()      # retry after the next interval, not every tick
            return False
