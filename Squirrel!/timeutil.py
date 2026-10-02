# timeutil.py - calendar arithmetic that depends neither on the platform epoch nor on libc
#
# Pure integer maths, so it behaves the same on the ESP32 port (epoch 2000) and on a PC.
# local_from_utc() applies a fixed standard offset plus the EU daylight-saving rule
# (summer time from 01:00 UTC on the last Sunday of March to 01:00 UTC on the last
# Sunday of October), which is what Poland uses.


def days_from_civil(y, m, d):
    """Days since 1970-01-01 for a proleptic Gregorian date."""
    if m <= 2:
        y -= 1
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(z):
    """Inverse of days_from_civil: (year, month, day)."""
    z += 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return (y + (1 if m <= 2 else 0), m, d)


def weekday_from_days(z):
    """0 = Monday ... 6 = Sunday (1970-01-01 was a Thursday)."""
    return (z + 3) % 7


def _last_sunday(year, month):
    z = days_from_civil(year, month, 31)        # March and October both have 31 days
    return z - (weekday_from_days(z) + 1) % 7


def local_from_utc(utc, std_offset_min=60, eu_dst=True):
    """(y, m, d, hh, mm, ss) in UTC -> (y, m, d, hh, mm, ss, weekday) in local time."""
    y, mo, d, h, mi, s = utc[:6]
    t = days_from_civil(y, mo, d) * 86400 + h * 3600 + mi * 60 + s
    offset = std_offset_min * 60
    if eu_dst:
        start = _last_sunday(y, 3) * 86400 + 3600
        end = _last_sunday(y, 10) * 86400 + 3600
        if start <= t < end:
            offset += 3600
    t += offset
    days, rem = divmod(t, 86400)
    ly, lm, ld = civil_from_days(days)
    return (ly, lm, ld, rem // 3600, (rem // 60) % 60, rem % 60, weekday_from_days(days))
