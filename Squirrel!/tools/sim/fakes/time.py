# time.py - a deterministic clock for the simulator: it only moves when the code sleeps
from utime import *
import utime as _u
import sim_state as _s


def ticks_ms():
    return _s.ms


def ticks_us():
    return _s.ms * 1000


def ticks_add(a, b):
    return a + b


def ticks_diff(a, b):
    return a - b


def sleep_ms(n):
    _s.ms += int(n)


def sleep_us(n):
    _s.ms += int(n) // 1000


def sleep(s):
    _s.ms += int(s * 1000)


def time():
    return _s.wall_s + _s.ms // 1000


def time_ns():
    return (_s.wall_s * 1000 + _s.ms) * 1000000


def localtime(secs=None):
    t = _u.gmtime(time() if secs is None else int(secs))
    return tuple(t[:8])


gmtime = localtime


def mktime(t):
    """UTC, like gmtime() above (the unix port's own mktime would use the PC's time zone)."""
    y, m, d = t[0], t[1], t[2]
    y -= m <= 2                                   # days from 1970-01-01 (H. Hinnant's days_from_civil)
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    days = era * 146097 + yoe * 365 + yoe // 4 - yoe // 100 + doy - 719468
    return days * 86400 + t[3] * 3600 + t[4] * 60 + t[5]
