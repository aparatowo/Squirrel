# appconfig.py - user settings kept in /sd/Squirrel/config.txt
#
# The rest of the program reads settings through the shared `cfg` object *at the moment it
# needs them* (cfg.get("KEY")), never from a constant imported once - that is what lets a
# change take effect without a restart.
#
#   * defaults ........ the same-named constants in nuts.py
#   * what exists .... appconfig_schema.SETTINGS (kind, range / options, label)
#   * the file ....... plain "KEY = value" lines, one per setting, with comments.  It is
#                      created with the defaults when missing, and a reset restores them.
#   * live changes ... cfg.set() applies at once and saves.  The values in memory are what the program
#                      uses; the file only brings them back after a restart.  It is NOT polled: it is
#                      read at start-up, by Settings -> Reload config, and checked once whenever the
#                      screen wakes up (check_file(): only its date and size; read again if they changed),
#                      so an edit made to it from a PC or Thonny is still picked up.
#   * listeners ...... cfg.on_change(fn) calls fn(key, new_value) for every value that changed.
#
# A value that cannot be understood never breaks anything: it falls back to the default and
# is reported in the log; the file is left untouched so the typo can be fixed.

import os
import nuts
from boot_log import log
from appconfig_schema import SETTINGS, HELP

_TRUE = ("true", "on", "yes", "1")
_FALSE = ("false", "off", "no", "0")
DAYS = "MTWTFSS"                 # kind "days": bit 0 = Monday


def time_text(minutes):
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def days_text(mask):
    """The days as config.txt stores them: MTWTFSS, '.' for a day that is not ticked."""
    return "".join(DAYS[i] if mask >> i & 1 else "." for i in range(7))


def days_shown(mask):
    """The days as the screen shows them: spaced out, '-' for a day that is not ticked ("M T W T F - -")."""
    return " ".join(DAYS[i] if mask >> i & 1 else "-" for i in range(7))


def _stamp(path):
    """(modification time, size) of a file, or None when it does not exist."""
    try:
        st = os.stat(path)
        return (st[8], st[6])
    except OSError:
        return None


def _ensure_parent(path):
    parent = path.rsplit("/", 1)[0]
    if not parent:
        return True
    try:
        os.stat(parent)
        return True
    except OSError:
        pass
    try:
        os.mkdir(parent)
        return True
    except Exception as e:
        log(f"[CONFIG] Cannot create {parent}: {e}")
        return False


class Config:
    def __init__(self):
        self._schema = {}          # key -> (kind, group, label, extra)
        self._order = []
        self._defaults = {}
        self._values = {}
        self._listeners = []
        self._extra = []           # lines of the file we do not recognise: kept when saving
        self._path = None
        self._stamp = None         # (mtime, size) as of our last read / write
        self.last_changed = 0      # results of the most recent (re)load, for the UI
        self.last_problems = 0
        for key, kind, group, label, extra in SETTINGS:
            self._schema[key] = (kind, group, label, extra)
            self._order.append(key)
            self._defaults[key] = self._values[key] = getattr(nuts, key)

    # ---------------- reading ----------------

    def get(self, key):
        return self._values[key]

    def default(self, key):
        return self._defaults[key]

    def is_default(self, key):
        return self._values[key] == self._defaults[key]

    def keys(self):
        return list(self._order)

    def groups(self):
        seen = []
        for key in self._order:
            group = self._schema[key][1]
            if group not in seen:
                seen.append(group)
        return seen

    def keys_in(self, group):
        return [k for k in self._order if self._schema[k][1] == group]

    def describe(self, key):
        """(kind, group, label, extra) - what a settings screen needs to edit the key."""
        return self._schema[key]

    @staticmethod
    def help(key):
        """What to know about the setting beyond its name ("" if nothing); lines are split by "\n"."""
        return HELP.get(key, "")

    def text_of(self, key):
        return self._to_text(self._schema[key][0], self._values[key])

    @property
    def path(self):
        return self._path

    # ---------------- changing ----------------

    def validate(self, key, value):
        """The value in canonical form, or ValueError.  Numbers are clamped to their range."""
        kind, _group, _label, extra = self._schema[key]
        if kind == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("not a whole number")
            lo, hi = extra[0], extra[1]
            return lo if value < lo else (hi if value > hi else value)
        if kind == "bool":
            if isinstance(value, bool):
                return value
            raise ValueError("expected true / false")
        if kind == "choice":
            if value in extra:
                return value
            raise ValueError("not one of the allowed values")
        if kind in ("time", "days"):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < (1440 if kind == "time" else 128):
                raise ValueError("expected HH:MM" if kind == "time" else "expected 7 days, e.g. MTWTF..")
            return value
        if kind == "color":
            if isinstance(value, str) and value.lower() in nuts.PALETTE:
                return value.lower()
            raise ValueError("unknown colour")
        if not isinstance(value, str) or "\n" in value or "\r" in value:   # text / secret
            raise ValueError("expected a single line of text")
        return value[:extra]

    def parse(self, key, text):
        """Turn the text after '=' into a value (ValueError when it makes no sense)."""
        kind, _group, _label, extra = self._schema[key]
        t = text.strip()
        if kind == "int":
            return self.validate(key, int(t))
        if kind == "bool":
            low = t.lower()
            if low in _TRUE:
                return True
            if low in _FALSE:
                return False
            raise ValueError("expected true / false")
        if kind == "choice":
            for option in extra:
                if str(option).lower() == t.lower():
                    return option
            raise ValueError("not one of the allowed values")
        if kind == "time":
            hours, sep, minutes = t.partition(":")
            if not sep or not hours.strip().isdigit() or not minutes.strip().isdigit():
                raise ValueError("expected HH:MM")
            h, m = int(hours), int(minutes)
            if h > 23 or m > 59:
                raise ValueError("expected HH:MM")
            return h * 60 + m
        if kind == "days":
            if len(t) != 7:
                raise ValueError("expected 7 days, e.g. MTWTF..")
            return sum(1 << i for i in range(7) if t[i] not in ".-_")
        return self.validate(key, t)

    def set(self, key, value, save=True):
        """Change one setting now (listeners run at once) and, by default, save the file."""
        value = self.validate(key, value)
        if value == self._values[key]:
            return value
        self._values[key] = value
        self._notify(key, value)
        if save:
            self.save()
        return value

    def reset(self, key=None, save=True):
        """Restore the default of one setting, or of all of them."""
        changed = False
        for k in ([key] if key else self._order):
            if self._values[k] != self._defaults[k]:
                self._values[k] = self._defaults[k]
                self._notify(k, self._defaults[k])
                changed = True
        if changed and save:
            self.save()
        return changed

    def on_change(self, callback):
        self._listeners.append(callback)

    def _notify(self, key, value):
        for callback in self._listeners:
            try:
                callback(key, value)
            except Exception as e:
                log(f"[CONFIG] Listener error for {key}: {e}")

    # ---------------- the file ----------------

    def load(self, path):
        """Use `path` as the config file: read it, or create it with the defaults.

        Returns 'loaded', 'created', 'unreadable' or 'unavailable' (no card / cannot write).
        """
        self._path = path
        tmp = path + ".tmp"
        if _stamp(path) is None and _stamp(tmp) is not None:      # a save was interrupted
            try:
                os.rename(tmp, path)
                log("[CONFIG] Recovered the file from an interrupted save")
            except OSError:
                pass
        stamp = _stamp(path)
        if stamp is None:
            if self.save():
                log(f"[CONFIG] No config file - created {path} with the defaults")
                return "created"
            log(f"[CONFIG] No config file and cannot create {path} - using the defaults")
            return "unavailable"
        self._stamp = stamp
        return self._read_file()

    def reload(self):
        """Re-read the file.  Returns (settings that changed, problems found), or None
        when there is no file to read (no card, or it was removed): the current values stay."""
        if not self._path:
            return None
        stamp = _stamp(self._path)
        if stamp is None:
            return None
        self._stamp = stamp
        self._read_file()
        return (self.last_changed, self.last_problems)

    def check_file(self):
        """Read the file again if it was edited outside the program (its date or size changed).  One os.stat() when
        it was not; called when the screen wakes up.  Returns what reload() returns, or None."""
        if not self._path:
            return None
        stamp = _stamp(self._path)
        if stamp is None or stamp == self._stamp:
            return None
        result = self.reload()
        if result is not None:
            log(f"[CONFIG] File edited: {result[0]} setting(s) changed, {result[1]} problem(s)")
        return result

    def save(self):
        """Write every setting.  tmp file + remove + rename, because FAT cannot rename over a file."""
        if not self._path or not _ensure_parent(self._path):
            return False
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w") as f:
                f.write(self._render())
            try:
                os.remove(self._path)
            except OSError:
                pass
            os.rename(tmp, self._path)
            self._stamp = _stamp(self._path)          # our own write must not look like an edit
            return True
        except Exception as e:
            log(f"[CONFIG] Save failed: {e}")
            return False

    def _read_file(self):
        try:
            with open(self._path, "r") as f:
                text = f.read()
        except Exception as e:
            log(f"[CONFIG] Cannot read {self._path}: {e}")
            self.last_changed, self.last_problems = 0, 1
            return "unreadable"
        overrides, problems, extra, seen = self._parse_text(text)
        self._extra = extra
        changed = 0
        for key in self._order:
            new = overrides.get(key, self._defaults[key])     # absent from the file = default
            if new != self._values[key]:
                self._values[key] = new
                self._notify(key, new)
                changed += 1
        for problem in problems:
            log(f"[CONFIG] {problem}")
        missing = [k for k in self._order if k not in seen]
        if missing and not problems:
            self.save()                    # a newer version added settings: append them
            log(f"[CONFIG] Added {len(missing)} new setting(s) to the file")
        self.last_changed, self.last_problems = changed, len(problems)
        return "loaded"

    def _parse_text(self, text):
        overrides, problems, extra, seen = {}, [], [], set()
        for raw in text.split("\n"):
            line = raw.strip()                  # also drops the \r of Windows line endings
            if not line or line[0] == "#":
                continue
            key, sep, value = line.partition("=")
            if not sep:
                problems.append("Ignored line without '=': " + line[:30])
                continue
            key = key.strip()
            if key not in self._schema:
                extra.append(line)
                continue
            seen.add(key)
            try:
                parsed = self.parse(key, value)
            except ValueError as e:
                problems.append("%s: %s - using the default" % (key, e))
                continue
            overrides[key] = parsed
            if self._schema[key][0] == "int" and parsed != int(value.strip()):
                problems.append("%s: %s is outside the allowed range - set to %d" % (key, value.strip(), parsed))
        return overrides, problems, extra, seen

    def _render(self):
        lines = [
            "# Squirrel! settings",
            "# Edit the value after '='. Lines starting with # are comments.",
            "# A value that is not understood falls back to the default. Delete this file to reset everything.",
            "",
        ]
        group = None
        for key in self._order:
            kind, g, label, extra = self._schema[key]
            if g != group:
                group = g
                lines.append("# --- %s ---" % g)
            lines.append("# %s%s" % (label, self._hint(kind, extra)))
            for help_line in HELP.get(key, "").split("\n"):
                if help_line:
                    lines.append("#   " + help_line)
            lines.append("%s = %s" % (key, self._to_text(kind, self._values[key])))
        if self._extra:
            lines.append("")
            lines.append("# Lines this version does not recognise (kept as they were)")
            lines.extend(self._extra)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _hint(kind, extra):
        if kind == "int":
            return " (%d to %d)" % (extra[0], extra[1])
        if kind == "bool":
            return " (true or false)"
        if kind == "choice":
            return " (" + ", ".join([str(o) for o in extra]) + ")"
        if kind == "color":
            return " (" + ", ".join(nuts.PALETTE) + ")"
        if kind == "time":
            return " (HH:MM)"
        if kind == "days":
            return " (MTWTFSS, '.' = not that day)"
        return " (up to %d characters)" % extra

    @staticmethod
    def _to_text(kind, value):
        if kind == "bool":
            return "true" if value else "false"
        if kind == "time":
            return time_text(value)
        if kind == "days":
            return days_text(value)
        return str(value)


# The one shared instance.  SquirrelApp loads the file once the SD card is mounted;
# until then it simply holds the defaults from nuts.py.
cfg = Config()
