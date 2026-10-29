# focus_timer.py - focus time counter that runs in the background
#
# States: 'stopped' (idle) -> 'running' <-> 'paused'.  Time is counted from
# time.ticks_ms(), so it does not depend on the RTC being right; the RTC only
# decides which calendar day the counted seconds belong to.
#
# The file <data_dir>/focus.txt holds "YYYY-MM-DD,seconds" lines; a day may have several (they add up).  Only TODAY's
# total is kept in memory - the status bars show it all the time - and it is read from the file once, when the day
# starts being counted.  New seconds are APPENDED (every 5 minutes while running, and on every pause / stop),
# so a save never reads the file.  The whole history is read only for the statistics (week()), which also rewrite
# the file with one line per day when it has more.
# Taking time back (a distraction counted as focus: subtract(), Focus -> Statistics) appends a NEGATIVE line
# ("2026-10-19,-900"); a day's lines add up and never go below zero.  reset_today() takes back the whole day.
# While it runs, the file <data_dir>/running exists: after a restart (a reset, new firmware, a crash) the timer goes on
# counting instead of being stopped without a word - only the seconds since the last save and the restart are lost.

import os
import time
from boot_log import log
from timeutil import days_from_civil, civil_from_days, weekday_from_days

_SAVE_INTERVAL_MS = 5 * 60 * 1000       # what a sudden restart can lose at most
_MIN_VALID_YEAR = 2024        # anything earlier means the clock was never set


def _key(y, m, d):
    return "%04d-%02d-%02d" % (y, m, d)


class FocusTimer:
    def __init__(self, rtc, data_dir, goal_seconds=6 * 3600):
        self._rtc = rtc
        self._dir = data_dir
        self._file = data_dir + "/focus.txt"
        self._tmp = data_dir + "/focus.tmp"
        self._running_file = data_dir + "/running"
        self._goal = goal_seconds      # a number, or a function returning it (read live)
        self.state = "stopped"
        self._day_key = None         # the day whose total is in memory
        self._day_secs = 0           # its total, saved and unsaved
        self._unsaved = {}           # "YYYY-MM-DD" -> seconds not appended to the file yet
        self._last_ms = 0
        self._frac_ms = 0
        self._last_save_ms = 0
        self._last_key = None
        self._recover()
        self._carry_on()

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
        self._run()
        self._mark_running(True)
        return "resumed" if was_paused else "started"

    def _run(self):
        now = time.ticks_ms()
        self.state = "running"
        self._last_ms = now
        self._frac_ms = 0
        self._last_save_ms = now

    def pause(self):
        if self.state == "running":
            self._accumulate(time.ticks_ms())
            self.state = "paused"
            self._save()
            self._mark_running(False)

    def stop(self):
        if self.state == "running":
            self._accumulate(time.ticks_ms())
            self._mark_running(False)
        if self.state != "stopped":
            self.state = "stopped"
            self._save()

    def start(self):
        """Start / resume, but never pause (the watch's double tap).  'started', 'resumed', 'running' or 'no_time'."""
        return "running" if self.state == "running" else self.toggle()

    def halt(self):
        """Pause, but never start (the watch's triple tap).  'paused', or 'not_running' when it was not counting."""
        if self.state != "running":
            return "not_running"
        self.pause()
        return "paused"

    def subtract(self, seconds):
        """Take `seconds` back from today's focus time (a distraction that was counted); never below zero.  A running
        timer keeps running.  Returns the seconds taken back (0: the clock is not set, or nothing counted today)."""
        key = self._today_key()
        if key is None:
            return 0
        if self.state == "running":
            self._accumulate(time.ticks_ms())
        self._use_day(key)
        n = min(int(seconds), self._day_secs)
        if n <= 0:
            return 0
        self._day_secs -= n
        self._unsaved[key] = self._unsaved.get(key, 0) - n
        self._save()
        log(f"[FOCUS] {n} s taken back from {key}")
        return n

    def reset_today(self):
        """Today's focus time back to zero.  Returns the seconds taken back."""
        return self.subtract(self.today_seconds())

    # ---------------- over a deep sleep (deep_sleep.py) ----------------

    def suspend(self):
        """Before a deep sleep: save what was counted; returns what resume() needs (JSON-able), or None."""
        if self.state == "running":
            self._accumulate(time.ticks_ms())
            self._save()
            return {"state": "running", "at": time.time()}
        if self.state == "paused":
            return {"state": "paused"}
        return None

    def resume(self, saved):
        """After a deep sleep: carry on; a running timer counts the time slept too (from the clock, up to a day)."""
        if not saved:
            return
        now = time.ticks_ms()
        if saved.get("state") == "running":
            slept = min(86400, max(0, time.time() - saved.get("at", time.time())))
            self.state = "running"
            self._last_ms = now
            self._frac_ms = slept * 1000
            self._last_save_ms = now
            self._accumulate(now)
        elif saved.get("state") == "paused":
            self.state = "paused"

    # ---------------- service tick ----------------

    def tick(self):
        if self.state != "running":
            return
        now = time.ticks_ms()
        self._accumulate(now)
        if self._unsaved and time.ticks_diff(now, self._last_save_ms) >= _SAVE_INTERVAL_MS:
            self._save()

    def _accumulate(self, now):
        self._frac_ms += time.ticks_diff(now, self._last_ms)
        self._last_ms = now
        seconds = self._frac_ms // 1000
        if seconds <= 0:
            return
        key = self._today_key() or self._last_key    # keep counting if the clock is being edited
        if key is None:
            return                     # no date yet (a restart, the clock not synced): the time waits for one
        self._frac_ms -= seconds * 1000
        self._last_key = key
        self._use_day(key)
        self._day_secs += seconds
        self._unsaved[key] = self._unsaved.get(key, 0) + seconds

    # ---------------- queries ----------------

    def indicator(self):
        return self.state

    def today_seconds(self):
        key = self._today_key()
        if key is None:
            return 0
        self._use_day(key)
        return self._day_secs

    def goal_reached(self):
        return self.today_seconds() >= self.goal_seconds

    def week(self, n=7):
        """Last n days, oldest first, ending today: [(date_key, weekday 0=Mon, seconds)].  Reads the file: call it when
        the statistics are opened, not on every redraw."""
        key = self._today_key()
        if key is None:
            return []
        days = self._read()
        for k, secs in self._unsaved.items():
            days[k] = days.get(k, 0) + secs
        base = days_from_civil(int(key[0:4]), int(key[5:7]), int(key[8:10]))
        result = []
        for back in range(n - 1, -1, -1):
            z = base - back
            y, m, d = civil_from_days(z)
            k = _key(y, m, d)
            result.append((k, weekday_from_days(z), days.get(k, 0)))
        return result

    def _use_day(self, key):
        """Make `key` the day kept in memory (its saved total is read from the file once)."""
        if key != self._day_key:
            self._day_key = key
            self._day_secs = self._read(only=key).get(key, 0) + self._unsaved.get(key, 0)

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

    def _mark_running(self, on):
        """The file that says "it was running" across a restart (see _carry_on)."""
        try:
            if on:
                if self._ensure_dir():
                    with open(self._running_file, "w") as f:
                        f.write("1")
            else:
                os.remove(self._running_file)
        except OSError:
            pass

    def _carry_on(self):
        """At start-up: running before a restart = running now (counting from now)."""
        try:
            os.stat(self._running_file)
        except OSError:
            return
        self._run()
        log("[FOCUS] was running before the restart: counting on")

    def _recover(self):
        """A save of the old kind (rewrite through focus.tmp) interrupted between remove and rename: keep the tmp."""
        try:
            os.stat(self._file)
            return
        except OSError:
            pass
        try:
            os.rename(self._tmp, self._file)
            log("[FOCUS] Recovered focus.txt from an interrupted save")
        except OSError:
            pass

    def _read(self, only=None):
        """{"YYYY-MM-DD": seconds} from the file (lines of the same day add up); only=key keeps just that day.
        Reading the whole history also rewrites the file with one line per day when it has more."""
        days, lines, bad = {}, 0, 0
        try:
            with open(self._file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        key, secs = line.split(",")
                        secs = int(secs)
                        if len(key) != 10 or key[4] != "-" or key[7] != "-":         # (secs < 0: taken back)
                            raise ValueError
                    except Exception:
                        bad += 1
                        continue
                    lines += 1
                    if only is None or key == only:
                        days[key] = days.get(key, 0) + secs
        except OSError:
            return days
        if bad:
            log(f"[FOCUS] {bad} bad line(s) in {self._file} skipped")
        for key in days:
            if days[key] < 0:
                days[key] = 0                       # more taken back than counted (a line lost): nothing, not less
        if only is None and lines > len(days):
            self._write_all(days)
        return days

    def _write_all(self, days):
        """Rewrite the file with one line per day; FAT cannot rename over an existing file, so: tmp, remove, rename."""
        try:
            with open(self._tmp, "w") as f:
                for key in sorted(days):
                    f.write("%s,%d\n" % (key, days[key]))
            try:
                os.remove(self._file)
            except OSError:
                pass
            os.rename(self._tmp, self._file)
        except Exception as e:
            log(f"[FOCUS] Cannot compact {self._file}: {e}")

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
        """Append the seconds counted since the last save (one line per day that has some)."""
        if not self._unsaved:
            return True
        if not self._ensure_dir():
            return False
        try:
            with open(self._file, "a") as f:
                for key in sorted(self._unsaved):
                    f.write("%s,%d\n" % (key, self._unsaved[key]))
            self._unsaved = {}
            self._last_save_ms = time.ticks_ms()
            return True
        except Exception as e:
            log(f"[FOCUS] Save failed: {e}")
            self._last_save_ms = time.ticks_ms()      # retry after the next interval, not every tick
            return False
