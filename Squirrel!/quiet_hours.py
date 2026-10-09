# quiet_hours.py - silent mode: hours of the night without sound (or light), set separately for the speaker, the buzzer
# and the LED
#
# Settings (group "Silent", Settings -> Silent mode): QUIET_<CHANNEL>_FROM / _TO (minutes after midnight) and
# QUIET_<CHANNEL>_DAYS (bit 0 = Monday).  From = To means no silent hours at all.  A night that crosses midnight
# belongs to the day it starts on: with Friday ticked, 22:00 - 06:00 is quiet from Friday 22:00 to Saturday 06:00.
#
# quiet_guard(channel) wraps a function that makes a sound: during the silent hours the call is skipped and the
# wrapper returns False.  The caller can pass force=True to sound anyway (a test, a tool the user has just started):
#
#     @quiet_guard("sound")
#     def beep(self, pattern, volume=None): ...
#
#     audio.beep("notify")                 # silent at night
#     audio.beep("tick", force=True)       # always
#
# While the clock has not been set the hours cannot be known, and nothing is silenced.

import time
from appconfig import cfg

CHANNELS = {"sound": "QUIET_SOUND", "buzzer": "QUIET_BUZZER", "led": "QUIET_LED"}
_MIN_YEAR = 2024                    # the same rule as scheduler.valid_now()


def keys(channel):
    """The names of the three settings of `channel`: (from, to, days)."""
    prefix = CHANNELS[channel]
    return (prefix + "_FROM", prefix + "_TO", prefix + "_DAYS")


def is_quiet(channel, settings=None, now=None):
    """True while `channel` ("sound" / "buzzer" / "led") is in its silent hours.

    settings: anything with .get(key) - the shared cfg by default, or values read straight from config.txt.
    now: a time.localtime() tuple, for tests."""
    settings = settings or cfg
    k_from, k_to, k_days = keys(channel)
    start, end, days = settings.get(k_from), settings.get(k_to), settings.get(k_days)
    if start == end or not days:
        return False
    t = now or time.localtime()
    if t[0] < _MIN_YEAR:
        return False
    minute, weekday = t[3] * 60 + t[4], t[6]
    if start < end:                                     # within one day, e.g. 13:00 - 15:00
        return start <= minute < end and bool(days >> weekday & 1)
    if minute >= start:                                 # the evening part of a night
        return bool(days >> weekday & 1)
    if minute < end:                                    # after midnight: the night began yesterday
        return bool(days >> ((weekday - 1) % 7) & 1)
    return False


def allowed(channel, settings=None):
    """The opposite of is_quiet(): may `channel` make a sound now?"""
    return not is_quiet(channel, settings)


def quiet_guard(channel, settings=None):
    """Decorator: skip the call (return False) during the silent hours of `channel`, unless force=True is passed.

    settings: what is_quiet() reads - an object with .get(key), or a function returning one at every call
    (so a value can be read fresh, e.g. straight from the file)."""
    def wrap(fn):
        def guarded(*args, **kwargs):
            if not kwargs.pop("force", False):
                source = settings() if callable(settings) else settings
                if is_quiet(channel, source):
                    return False
            return fn(*args, **kwargs)
        return guarded
    return wrap
