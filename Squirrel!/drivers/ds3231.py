# ds3231.py - the DS3231 clock chip on I2C: temperature-compensated, kept running by its coin cell
#
# Its OSF bit (status register, bit 7) says the oscillator stopped at some point (no battery, first power-up) and the
# time is not to be trusted; it stays set until it is cleared.  read_valid() refuses such a time (the app then waits for
# a time to be set), set_datetime() writes the time and clears OSF.
#
# The alarm is the chip's Alarm 2 (to the minute: minute, hour, day of the month - like the PCF8563's): when it comes,
# the chip sets A2F and pulls its INT/SQW line low until A2F is cleared (open drain: the line needs a pull-up).
# set_alarm(dt) / set_alarm(None); alarm_fired() reads A2F, clear_alarm_flag() releases the line.
# The constructor raises OSError when nothing answers at the address: the board can then try another clock chip.
from hw.rtc_base import TimeProvider

_ADDR = 0x68
_REG_TIME = 0x00                # seconds, minutes, hours, weekday, date, month (+ century), year
_REG_ALARM2 = 0x0B              # minutes, hours, day / date
_REG_CONTROL = 0x0E
_REG_STATUS = 0x0F
_INTCN, _A2IE = 0x04, 0x02      # control: INT/SQW is the alarm line (not a square wave); Alarm 2 drives it
_OSF, _A2F = 0x80, 0x02         # status: the oscillator stopped; Alarm 2 came


def _bcd(v):
    return (v >> 4) * 10 + (v & 0x0F)


def _tobcd(v):
    return (v // 10) << 4 | (v % 10)


class DS3231TimeProvider(TimeProvider):
    def __init__(self, i2c, addr=_ADDR):
        self.i2c = i2c
        self.addr = addr
        self.i2c.readfrom_mem(addr, _REG_STATUS, 1)        # OSError: no DS3231 on this bus

    @property
    def is_available(self):
        try:
            self.i2c.readfrom_mem(self.addr, _REG_STATUS, 1)
            return True
        except OSError:
            return False

    def _read(self):
        d = self.i2c.readfrom_mem(self.addr, _REG_TIME, 7)
        h = d[2]
        if h & 0x40:                                       # 12-hour mode (never set by this driver): bit 5 = PM
            hour = _bcd(h & 0x1F) % 12 + (12 if h & 0x20 else 0)
        else:
            hour = _bcd(h & 0x3F)
        year = 2000 + _bcd(d[6]) + (100 if d[5] & 0x80 else 0)
        dt = (year, _bcd(d[5] & 0x1F), _bcd(d[4] & 0x3F), hour, _bcd(d[1] & 0x7F), _bcd(d[0] & 0x7F),
              ((d[3] & 0x07) + 6) % 7, 0)                  # the chip's weekday is 1..7 (ours: 0 = Monday, written +1)
        return dt, bool(self.i2c.readfrom_mem(self.addr, _REG_STATUS, 1)[0] & _OSF)

    def get_datetime(self):
        return self._read()[0]

    def read_valid(self):
        dt, osf = self._read()
        if osf:
            raise OSError("DS3231: the time is not valid (OSF - the oscillator stopped)")
        if not 2025 <= dt[0] <= 2099 or not 1 <= dt[1] <= 12 or not 1 <= dt[2] <= 31:
            raise OSError("DS3231: implausible time %r" % (dt[:6],))
        return dt

    def set_datetime(self, dt):
        year, month, mday, hour, minute, second, weekday = dt[:7]
        century = 0x80 if year >= 2100 else 0
        self.i2c.writeto_mem(self.addr, _REG_TIME, bytes([_tobcd(second), _tobcd(minute), _tobcd(hour),
                                                         weekday % 7 + 1, _tobcd(mday), _tobcd(month) | century,
                                                         _tobcd(year % 100)]))
        status = self.i2c.readfrom_mem(self.addr, _REG_STATUS, 1)[0]
        self.i2c.writeto_mem(self.addr, _REG_STATUS, bytes([status & ~_OSF & 0xFF]))

    has_alarm = True

    def set_alarm(self, dt):
        """Arm Alarm 2 for dt's day / hour / minute (seconds are ignored), or disarm it (None).  A2F is cleared."""
        control = self.i2c.readfrom_mem(self.addr, _REG_CONTROL, 1)[0]
        if dt is None:
            self.i2c.writeto_mem(self.addr, _REG_CONTROL, bytes([(control | _INTCN) & ~_A2IE & 0xFF]))
        else:
            # A2M2..A2M4 = 0 and DY/DT = 0: minute, hour and date must all match
            self.i2c.writeto_mem(self.addr, _REG_ALARM2, bytes([_tobcd(dt[4]), _tobcd(dt[3]), _tobcd(dt[2])]))
            self.i2c.writeto_mem(self.addr, _REG_CONTROL, bytes([control | _INTCN | _A2IE]))
        self.clear_alarm_flag()

    def alarm_fired(self):
        return bool(self.i2c.readfrom_mem(self.addr, _REG_STATUS, 1)[0] & _A2F)

    def clear_alarm_flag(self):
        """Release the INT/SQW line (A2F = 0); the alarm stays as it is."""
        status = self.i2c.readfrom_mem(self.addr, _REG_STATUS, 1)[0]
        self.i2c.writeto_mem(self.addr, _REG_STATUS, bytes([status & ~_A2F & 0xFF]))

    def temperature(self):
        """The chip's own temperature sensor, in degrees Celsius (0.25 steps; it is updated every 64 s)."""
        t = self.i2c.readfrom_mem(self.addr, 0x11, 2)
        raw = (t[0] << 2) | (t[1] >> 6)
        return (raw - 1024 if raw & 0x200 else raw) / 4
