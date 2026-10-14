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
from timeutil import days_from_civil, civil_from_days, weekday_from_days, weekday as weekday_of, wire_time, wire_now

_MIN_YEAR = 2024
DAYS = "MTWTFSS"
_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


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


class EventLog:
    """The routine log (data-format.md 3.6): what became of every routine that came up, in "id,at,result" lines
    (at = the time it was set for, in the shared format's seconds).  Appended to; trim() keeps the last keep_s."""

    RESULTS = ("done", "skip", "missed")

    def __init__(self, path, keep_s=60 * 86400):
        self._path = path
        self._keep = keep_s

    def add(self, rid, at, result):
        folder = self._path.rpartition("/")[0]
        if folder:
            try:
                os.mkdir(folder)
            except OSError:
                pass                                  # there already
        try:
            with open(self._path, "a") as f:
                f.write("%d,%d,%s\n" % (rid, at, result))
        except OSError as e:
            log(f"[ROUTINE] cannot write the log: {e}")

    def since(self, t=0):
        """[{"r", "at", "res"}] of the events set for after t, oldest first."""
        out = []
        try:
            with open(self._path) as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) == 3 and parts[2] in self.RESULTS:
                        try:
                            at = int(parts[1])
                            if at > t:
                                out.append({"r": int(parts[0]), "at": at, "res": parts[2]})
                        except ValueError:
                            pass
        except OSError:
            pass
        return out

    def trim(self, now):
        """Drop the events older than keep_s; returns how many went."""
        try:
            with open(self._path) as f:
                lines = f.read().split("\n")
        except OSError:
            return 0
        keep = [l for l in lines if l and _event_at(l) >= now - self._keep]
        dropped = len([l for l in lines if l]) - len(keep)
        if dropped:
            try:
                with open(self._path, "w") as f:
                    f.write("".join(l + "\n" for l in keep))
            except OSError as e:
                log(f"[ROUTINE] cannot trim the log: {e}")
                return 0
        return dropped


def _event_at(line):
    try:
        return int(line.split(",")[1])
    except (IndexError, ValueError):
        return 0


class RoutineStore:
    """The routines in routines.json, records of data-format.md 3.1: [{"id", "t": text, "h": hour, "m": minute,
    "d": days bitmask (bit 0 = Monday), "on": bool, "to": devices (bit n = slot n), "e": edited, "c": on/off changed}].
    Files of version 1.x have no id / to / e / c: the routines get them when the file is read (and it is written back).
    slot: this device's slot (0 = the head or a device on its own); a routine comes up only where its "to" has it."""

    def __init__(self, path, slot=0):
        self._path = path
        self.slot = slot
        self.items = []
        try:
            with open(path) as f:
                data = json.loads(f.read())
        except (OSError, ValueError):
            return
        if not isinstance(data, list):
            return
        missing = False
        for r in data:
            try:                                      # one damaged entry must not cost the others
                item = {"t": str(r.get("t", ""))[:50], "h": int(r.get("h", 8)) % 24, "m": int(r.get("m", 0)) % 60,
                        "d": int(r.get("d", 127)) & 127, "on": bool(r.get("on", True)),
                        "to": int(r.get("to", 255)) & 255, "e": int(r.get("e", 0)), "c": int(r.get("c", 0))}
                if isinstance(r.get("id"), int) and 0 < r["id"] < 65536:
                    item["id"] = r["id"]
                else:
                    missing = True
                self.items.append(item)
            except (AttributeError, ValueError, TypeError):
                pass
        if missing:
            from ble.merge import next_id
            for item in self.items:
                if "id" not in item:
                    item["id"] = next_id([i for i in self.items if "id" in i], self.slot)
            self.save()

    def create(self):
        """A new routine (added to the list); the caller saves."""
        from ble.merge import next_id
        from i18n import _ as tr
        r = {"id": next_id(self.items, self.slot), "t": tr("Routine"), "h": 8, "m": 0, "d": 127, "on": True, "to": 255,
             "e": wire_now(), "c": 0}
        self.items.append(r)
        return r

    @staticmethod
    def edited(r):
        """The content of r changed (text, time, days, devices)."""
        r["e"] = wire_now()

    @staticmethod
    def state_changed(r):
        """r was switched on / off."""
        r["c"] = wire_now()

    def comes_up(self, r, weekday):
        return r["on"] and r["d"] >> weekday & 1 and r.get("to", 255) >> self.slot & 1

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

    def __init__(self, store, notifier, audio, cfg, routines_done, todo_editor=None, now_ms=None, events=None):
        self.store = store
        self._events = events                # EventLog, or None
        self._notifier = notifier
        self._audio = audio
        self._cfg = cfg
        self._done = routines_done           # DayCounter
        self._todo = todo_editor
        self._now_ms = now_ms or time.ticks_ms
        self._last_check = -10000
        self._minute = None
        self._day = None
        self._snoozed = []                   # [fire_at_ms, routine, snooze number, fire_at (epoch seconds), set for (wire)]

    def tick(self):
        now = self._now_ms()
        if time.ticks_diff(now, self._last_check) < 500:      # light sleep wakes every 0.8 s: a 1 s limit would skip every second wake
            return
        self._last_check = now
        for entry in list(self._snoozed):
            if time.ticks_diff(now, entry[0]) >= 0:
                self._snoozed.remove(entry)
                self._fire(entry[1], entry[2], entry[4])
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
        if self._events is not None:
            try:
                self._events.trim(wire_now())
            except Exception as e:
                log(f"[ROUTINE] log clean-up failed: {e}")
        if self._todo is not None:
            try:
                n = self._todo.purge()
                if n:
                    log(f"[TODO] {n} done To-Do(s) older than {self._cfg.get('TODO_KEEP_DAYS')} days deleted")
            except Exception as e:
                log(f"[TODO] clean-up failed: {e}")

    def _on_minute(self, t):
        hour, minute, weekday = t[3], t[4], weekday_of(t)
        for routine in self.store.items:
            if self.store.comes_up(routine, weekday) and routine["h"] == hour and routine["m"] == minute:
                log("[ROUTINE] %r %02d:%02d %s - now %s %s" % (routine["t"], hour, minute, RoutineStore.days_text(routine["d"]),
                                                              day_key(t), _DAY_NAMES[weekday]))
                self._fire(routine, 0, wire_time((t[0], t[1], t[2], hour, minute, 0)))
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

    def _fire(self, routine, snooze_number, at):
        from notifier import Notification
        from i18n import _
        title = _("Routine %02d:%02d") % (routine["h"], routine["m"])
        self._notifier.post(Notification(
            routine["t"] or _("Routine"), title=title, timeout_s=30,
            on_done=lambda: self._completed(routine, at), on_cancel=lambda: self._record(routine, at, "skip"),
            on_timeout=lambda: self._snooze(routine, snooze_number, at),
            done_label="Done", cancel_label="Skip"))

    def _record(self, routine, at, result):
        if self._events is not None and "id" in routine:
            self._events.add(routine["id"], at, result)

    def _completed(self, routine, at):
        t = valid_now()
        if t is not None:
            self._done.add(day_key(t), 1)
        self._record(routine, at, "done")

    def _snooze(self, routine, number, at):
        if number >= nuts.ROUTINE_MAX_SNOOZES:
            self._record(routine, at, "missed")
            return
        minutes = self._cfg.get("ROUTINE_SNOOZE_MIN")
        self._snoozed.append([time.ticks_add(self._now_ms(), minutes * 60000), routine, number + 1,
                              time.time() + minutes * 60, at])

    # ---- the alarm queue (alarms.py) and the deep sleep (deep_sleep.py) ----

    def events(self, now, until):
        """[(epoch, label)] of what this scheduler will do between now and until: routines, the cuckoo, snoozes."""
        from i18n import _ as tr                              # (_ is the loop variable below)
        out = [(e[3], tr("Snoozed: %s") % (e[1]["t"] or tr("Routine"))) for e in self._snoozed if now < e[3] <= until]
        t = time.localtime(now)
        if t[0] < _MIN_YEAR:
            return out
        today = days_from_civil(t[0], t[1], t[2])
        midnight = now - (t[3] * 3600 + t[4] * 60 + t[5])
        for k in range(8):                                    # today and the next 7 days
            weekday = weekday_from_days(today + k)
            for routine in self.store.items:
                if self.store.comes_up(routine, weekday):
                    at = midnight + k * 86400 + routine["h"] * 3600 + routine["m"] * 60
                    if now < at <= until:
                        out.append((at, routine["t"] or tr("Routine")))
        if self._cfg.get("CUCKOO_ENABLED"):
            step = 900 if self._cfg.get("CUCKOO_QUARTERS") else 3600
            at = now - (now - midnight) % step + step          # the next quarter / full hour
            for _ in range(8):
                if at > until:
                    break
                out.append((at, tr("Cuckoo") if (at - midnight) % 3600 == 0 else tr("Cuckoo (quarter)")))
                at += step
        return out

    def export_snoozes(self):
        """The snoozed routines as JSON-able data (kept over a deep sleep)."""
        return [[e[3], e[1], e[2], e[4]] for e in self._snoozed]

    def import_snoozes(self, items):
        now_ms, now = self._now_ms(), time.time()
        for item in items:
            at, routine, number = item[:3]
            set_for = item[3] if len(item) > 3 else 0           # saved by version 1.x: not known
            self._snoozed.append([time.ticks_add(now_ms, max(0, at - now) * 1000), routine, number, at, set_for])
