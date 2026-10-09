# scheduler.py - things that happen at a time of day: routines, the cuckoo clock, the daily clean-up
#
# Also home of DayCounter, the small per-day tally behind the statistics (routines done, To-Dos done).
# The clock is the device's internal one, which this app keeps in LOCAL time; before it has been set
# (year < 2024) nothing here fires and nothing is counted under a wrong date.

import json
import os
import time
import nuts
from boot_log import log
from hw.buzzer import signal
from hw.led import signal as led_signal
from timeutil import days_from_civil, civil_from_days, weekday_from_days

_MIN_YEAR = 2024
DAYS = "MTWTFSS"


def valid_now():
    """time.localtime() once the clock has been set, else None."""
    t = time.localtime()
    return t if t[0] >= _MIN_YEAR else None


def day_key(t):
    return "%04d-%02d-%02d" % (t[0], t[1], t[2])



class DayCounter:
    """Counts per calendar day (routines done, To-Dos done), in a text file of "YYYY-MM-DD,count" lines.

    Nothing is kept in memory and the file is not read at start-up: add() appends one line ("2026-10-09,1", or ",-1"
    when a To-Do is un-ticked), and the totals are read only when they are asked for (get(), week() - the statistics).
    Reading adds the lines up per day and, when the file holds more lines than days (or days older than keep_days),
    writes it back with one line per day."""

    def __init__(self, path, keep_days=60):
        self._path = path
        self._keep = keep_days
        self._folder_ok = False

    def add(self, key, n=1):
        try:
            if not self._folder_ok:
                folder = self._path.rpartition("/")[0]
                if folder:
                    try:
                        os.mkdir(folder)
                    except OSError:
                        pass
                self._folder_ok = True
            with open(self._path, "a") as f:
                f.write("%s,%d\n" % (key, n))
        except OSError as e:
            self._folder_ok = False
            log(f"[COUNT] cannot save {self._path}: {e}")

    def totals(self):
        """{"YYYY-MM-DD": count} read from the file now."""
        days, lines = {}, 0
        try:
            with open(self._path) as f:
                for line in f:
                    key, _sep, n = line.strip().partition(",")
                    try:
                        n = int(n)
                    except ValueError:
                        continue
                    if len(key) == 10:
                        days[key] = max(0, days.get(key, 0) + n)     # in order: an un-tick never goes below zero
                        lines += 1
        except OSError:
            return days
        if lines > len(days) or len(days) > self._keep:
            days = self._compact(days)
        return days

    def get(self, key):
        return self.totals().get(key, 0)

    def week(self, n=7):
        """[(key, weekday 0=Mon, count)] for the n days up to today, oldest first."""
        t = valid_now()
        if t is None:
            return [("", i, 0) for i in range(n)]
        days = self.totals()
        today = days_from_civil(t[0], t[1], t[2])
        out = []
        for z in range(today - n + 1, today + 1):
            y, m, d = civil_from_days(z)
            key = "%04d-%02d-%02d" % (y, m, d)
            out.append((key, weekday_from_days(z), days.get(key, 0)))
        return out

    def _compact(self, days):
        newest = sorted(days)[-self._keep:]
        days = {k: days[k] for k in newest}
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w") as f:
                for k in newest:
                    f.write("%s,%d\n" % (k, days[k]))
            try:
                os.remove(self._path)
            except OSError:
                pass
            os.rename(tmp, self._path)
        except OSError as e:
            log(f"[COUNT] cannot compact {self._path}: {e}")
        return days


class RoutineStore:
    """The routines in routines.json: [{"t": text, "h": hour, "m": minute, "d": days bitmask (bit 0 = Monday), "on": bool}]."""

    def __init__(self, path):
        self._path = path
        self.items = []
        try:
            with open(path) as f:
                data = json.loads(f.read())
        except (OSError, ValueError):
            return
        if not isinstance(data, list):
            return
        for r in data:
            try:                                      # one damaged entry must not cost the others
                self.items.append({"t": str(r.get("t", ""))[:50], "h": int(r.get("h", 8)) % 24, "m": int(r.get("m", 0)) % 60,
                                   "d": int(r.get("d", 127)) & 127, "on": bool(r.get("on", True))})
            except (AttributeError, ValueError, TypeError):
                pass

    @staticmethod
    def new():
        return {"t": "Routine", "h": 8, "m": 0, "d": 127, "on": True}

    def save(self):
        try:
            with open(self._path, "w") as f:
                f.write(json.dumps(self.items))
            return True
        except OSError as e:
            log(f"[ROUTINE] cannot save: {e}")
            return False

    @staticmethod
    def days_text(mask):
        """Compact form ("MTWTF.."); the screens show appconfig.days_shown() instead."""
        return "".join(DAYS[i] if mask >> i & 1 else "." for i in range(7))


class Scheduler:
    """Service: fires routines (a notification with a sound), plays the cuckoo, runs the daily clean-up."""

    def __init__(self, store, notifier, audio, cfg, routines_done, todo_editor=None, now_ms=None):
        self.store = store
        self._notifier = notifier
        self._audio = audio
        self._cfg = cfg
        self._done = routines_done           # DayCounter
        self._todo = todo_editor
        self._now_ms = now_ms or time.ticks_ms
        self._last_check = -10000
        self._minute = None
        self._day = None
        self._snoozed = []                   # [fire_at_ms, routine, snooze number]

    def tick(self):
        now = self._now_ms()
        if time.ticks_diff(now, self._last_check) < 500:      # light sleep wakes every 0.8 s: a 1 s limit would skip every second wake
            return
        self._last_check = now
        for entry in list(self._snoozed):
            if time.ticks_diff(now, entry[0]) >= 0:
                self._snoozed.remove(entry)
                self._fire(entry[1], entry[2])
        t = valid_now()
        if t is None:
            return
        key = (t[0], t[1], t[2], t[3], t[4])
        if key == self._minute:
            return
        self._minute = key
        if day_key(t) != self._day:
            self._day = day_key(t)
            self._clean_up()
        self._on_minute(t)

    def _clean_up(self):
        if self._todo is not None:
            try:
                n = self._todo.purge()
                if n:
                    log(f"[TODO] {n} done To-Do(s) older than {self._cfg.get('TODO_KEEP_DAYS')} days deleted")
            except Exception as e:
                log(f"[TODO] clean-up failed: {e}")

    def _on_minute(self, t):
        hour, minute, weekday = t[3], t[4], t[6]
        for routine in self.store.items:
            if routine["on"] and routine["d"] >> weekday & 1 and routine["h"] == hour and routine["m"] == minute:
                self._fire(routine, 0)
        if self._cfg.get("CUCKOO_ENABLED"):
            if minute == 0:
                log(f"[CUCKOO] {hour:02d}:00")          # one line an hour: the proof that it was meant to sound
                self._audio.beep("cuckoo")
                signal("BUZZER_CUCKOO", "double")
                led_signal("LED_CUCKOO")
            elif minute % 15 == 0 and self._cfg.get("CUCKOO_QUARTERS"):
                self._audio.beep("tick", volume=self._cfg.get("CUCKOO_QUARTER_VOLUME"))
                signal("BUZZER_CUCKOO", "click")
                led_signal("LED_CUCKOO")

    def _fire(self, routine, snooze_number):
        from notifier import Notification
        title = "Routine %02d:%02d" % (routine["h"], routine["m"])
        self._notifier.post(Notification(
            routine["t"] or "Routine", title=title, timeout_s=30,
            on_done=lambda: self._completed(), on_cancel=None,
            on_timeout=lambda: self._snooze(routine, snooze_number),
            done_label="Done", cancel_label="Skip"))

    def _completed(self):
        t = valid_now()
        if t is not None:
            self._done.add(day_key(t), 1)

    def _snooze(self, routine, number):
        if number >= nuts.ROUTINE_MAX_SNOOZES:
            return
        minutes = self._cfg.get("ROUTINE_SNOOZE_MIN")
        self._snoozed.append([time.ticks_add(self._now_ms(), minutes * 60000), routine, number + 1])
