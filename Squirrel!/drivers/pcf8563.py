# pcf8563.py - the PCF8563 clock chip (T-Watch 2020): kept running by the battery
#
# Its VL bit (seconds register, bit 7) says the clock lost power at some point and the time is not to be trusted; it
# stays set until the time is written.  read_valid() refuses such a time (the app then waits for a time to be set),
# set_datetime() writes the time and so clears VL.
#
# The alarm (to the minute: minute, hour, day of the month - the weekday is not used): when it comes, the chip sets AF
# and pulls its INT line low (GPIO37 on the watch) until AF is cleared - what wakes the ESP32 from a deep sleep.
# set_alarm(dt) / set_alarm(None); alarm_fired() reads AF, clear_alarm_flag() releases the line.
from hw.rtc_base import TimeProvider

_ADDR = 0x51


def _bcd(v):
    return (v >> 4) * 10 + (v & 0x0F)


def _tobcd(v):
    return (v // 10) << 4 | (v % 10)


class PCF8563TimeProvider(TimeProvider):
    def __init__(self, i2c):
        self.i2c = i2c

    @property
    def is_available(self):
        try:
            self.i2c.readfrom_mem(_ADDR, 0x02, 1)
            return True
        except OSError:
            return False

    def _read(self):
        d = self.i2c.readfrom_mem(_ADDR, 0x02, 7)
        year = 2000 + _bcd(d[6]) + (100 if d[5] & 0x80 else 0)
        dt = (year, _bcd(d[5] & 0x1F), _bcd(d[3] & 0x3F), _bcd(d[2] & 0x3F), _bcd(d[1] & 0x7F), _bcd(d[0] & 0x7F),
              ((d[4] & 0x07) + 6) % 7, 0)         # the chip: 0 = Sunday; ours: 0 = Monday
        return dt, bool(d[0] & 0x80)

    def get_datetime(self):
        return self._read()[0]

    def read_valid(self):
        dt, vl = self._read()
        if vl:
            raise OSError("PCF8563: the time is not valid (VL - the clock lost power)")
        if not 2025 <= dt[0] <= 2099 or not 1 <= dt[1] <= 12 or not 1 <= dt[2] <= 31:
            raise OSError("PCF8563: implausible time %r" % (dt[:6],))
        return dt

    has_alarm = True

    def set_alarm(self, dt):
        """Arm the alarm for dt's day / hour / minute (seconds are ignored), or disarm it (None).  AF is cleared."""
        if dt is None:
            self.i2c.writeto_mem(_ADDR, 0x09, b"\x80\x80\x80\x80")       # every field disabled
            self.i2c.writeto_mem(_ADDR, 0x01, b"\x00")                    # AIE off, AF cleared
            return
        self.i2c.writeto_mem(_ADDR, 0x09, bytes([_tobcd(dt[4]), _tobcd(dt[3]), _tobcd(dt[2]), 0x80]))
        self.i2c.writeto_mem(_ADDR, 0x01, b"\x02")                        # AIE on, AF cleared

    def alarm_fired(self):
        return bool(self.i2c.readfrom_mem(_ADDR, 0x01, 1)[0] & 0x08)

    def clear_alarm_flag(self):
        """Release the INT line (AF = 0); the alarm stays as it is."""
        c = self.i2c.readfrom_mem(_ADDR, 0x01, 1)[0]
        self.i2c.writeto_mem(_ADDR, 0x01, bytes([c & ~0x08 & 0x1F]))

    def set_datetime(self, dt):
        year, month, mday, hour, minute, second, weekday = dt[:7]
        century = 0x80 if year >= 2100 else 0
        self.i2c.writeto_mem(_ADDR, 0x02, bytes([_tobcd(second) & 0x7F, _tobcd(minute), _tobcd(hour), _tobcd(mday),
                                                 (weekday + 1) % 7, _tobcd(month) | century, _tobcd(year % 100)]))
