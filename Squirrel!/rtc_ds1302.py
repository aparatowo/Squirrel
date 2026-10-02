# rtc_ds1302.py — DS1302 hardware RTC adapter
#
# Implements TimeProvider using the DS1302 chip connected over a
# 3-wire serial bus (CLK / DAT / RST).  Pure MicroPython bit-bang
# driver — no external library required.
#
# Wiring (Cardputer):
#   DS1302 CLK  ->  GPIO 6
#   DS1302 DAT  ->  GPIO 4
#   DS1302 RST  ->  GPIO 3
#   DS1302 VCC  ->  3.3 V
#   DS1302 GND  ->  GND

import time
from machine import Pin
from rtc_base import TimeProvider


# DS1302 register addresses (write addresses; read = write | 0x01)
_REG_SECONDS = 0x80
_REG_MINUTES = 0x82
_REG_HOURS   = 0x84
_REG_DATE    = 0x86
_REG_MONTH   = 0x88
_REG_WEEKDAY = 0x8A
_REG_YEAR    = 0x8C
_REG_CONTROL = 0x8E   # bit7=1 write-protect, bit7=0 write-enable
_REG_BURST   = 0xBE   # clock-burst write (8 bytes at once)


_MIN_VALID_YEAR = 2025      # a factory-fresh chip reads 2000-01-01: not a real time


def _bcd_ok(value: int) -> bool:
    return (value >> 4) <= 9 and (value & 0x0F) <= 9


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        return 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    return 30 if month in (4, 6, 9, 11) else 31


def _bcd_to_int(bcd: int) -> int:
    return (bcd >> 4) * 10 + (bcd & 0x0F)


def _int_to_bcd(value: int) -> int:
    return ((value // 10) << 4) | (value % 10)


class DS1302TimeProvider(TimeProvider):
    """Hardware RTC adapter for the DS1302 chip.

    The driver bit-bangs the 3-wire protocol directly — no dependency on
    any external library.  Raises RuntimeError on construction when the
    chip does not respond (used by RTCManager to detect absence).
    """

    def __init__(self, clk_pin: int, dat_pin: int, rst_pin: int):
        self._clk = Pin(clk_pin, Pin.OUT)
        self._dat = Pin(dat_pin, Pin.OUT)
        self._rst = Pin(rst_pin, Pin.OUT)

        self._clk.value(0)
        self._rst.value(0)

        # Verify chip is reachable by reading seconds register.
        # A stuck bus returns 0xFF; a missing chip holds the line low (0x00).
        # Either value is suspicious — we do a write-then-read sanity check.
        self._write_protect(False)
        raw = self._read_reg(_REG_SECONDS | 0x01)
        if raw == 0xFF:
            raise RuntimeError("DS1302 not found (bus stuck high)")

        self._available = True
        print(f"[RTC] DS1302 detected. Raw seconds register: 0x{raw:02X}")

    # ------------------------------------------------------------------
    # TimeProvider interface
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._available

    def get_datetime(self) -> tuple:
        """Read all registers in burst mode and return 8-tuple."""
        regs = self._burst_read()
        second  = _bcd_to_int(regs[0] & 0x7F)   # mask CH (clock-halt) bit
        minute  = _bcd_to_int(regs[1] & 0x7F)
        hour    = _bcd_to_int(regs[2] & 0x3F)   # mask 12/24 bit
        mday    = _bcd_to_int(regs[3] & 0x3F)
        month   = _bcd_to_int(regs[4] & 0x1F)
        weekday = _bcd_to_int(regs[5] & 0x07) - 1  # DS1302: 1-7 → 0-6
        year    = _bcd_to_int(regs[6]) + 2000

        # MicroPython localtime tuple: (year, month, mday, hour, min, sec, weekday, yearday)
        return (year, month, mday, hour, minute, second, weekday % 7, 0)

    @staticmethod
    def _decode_checked(regs) -> tuple:
        """Decode burst registers; raise ValueError for anything implausible."""
        if regs[0] & 0x80:
            raise ValueError("oscillator halted (no valid time stored)")
        if regs[2] & 0x80:
            raise ValueError("12-hour mode (not written by this app)")
        masked = (regs[0] & 0x7F, regs[1] & 0x7F, regs[2] & 0x3F, regs[3] & 0x3F,
                  regs[4] & 0x1F, regs[5] & 0x07, regs[6])
        for value in masked:
            if not _bcd_ok(value):
                raise ValueError("invalid BCD digits (bus floating?)")
        second, minute, hour, mday, month, weekday, year = [_bcd_to_int(v) for v in masked]
        year += 2000
        if (year < _MIN_VALID_YEAR or not 1 <= month <= 12
                or not 1 <= mday <= _days_in_month(year, month)
                or hour > 23 or minute > 59 or second > 59 or not 1 <= weekday <= 7):
            raise ValueError("date/time out of range")
        return (year, month, mday, hour, minute, second, (weekday - 1) % 7, 0)

    def read_valid(self, attempts: int = 3) -> tuple:
        """Return a plausible datetime or raise ValueError.

        Two readings 30 ms apart must agree (seconds may advance by at most 2), which
        rejects the random values a floating, unconnected bus produces.
        """
        error = "no reading"
        for _ in range(attempts):
            try:
                first = self._decode_checked(self._burst_read())
                time.sleep_ms(30)
                second = self._decode_checked(self._burst_read())
            except ValueError as e:
                error = str(e)
                continue
            if first[:5] == second[:5] and 0 <= second[5] - first[5] <= 2:
                return second
            error = "unstable reading (bus floating?)"
        raise ValueError(error)

    def set_datetime(self, dt: tuple) -> None:
        """Write datetime from 8-tuple (year, month, mday, hour, min, sec, weekday, yearday)."""
        year, month, mday, hour, minute, second, weekday, _ = dt
        self._write_protect(False)
        self._burst_write(
            _int_to_bcd(second),
            _int_to_bcd(minute),
            _int_to_bcd(hour),
            _int_to_bcd(mday),
            _int_to_bcd(month),
            _int_to_bcd((weekday % 7) + 1),   # 0-6 → 1-7
            _int_to_bcd(year - 2000),
            0x00,   # control byte (write-protect off)
        )

    # ------------------------------------------------------------------
    # Low-level 3-wire protocol
    # ------------------------------------------------------------------

    def _write_protect(self, enable: bool) -> None:
        self._write_reg(_REG_CONTROL, 0x80 if enable else 0x00)

    def _start(self) -> None:
        self._rst.value(0)
        self._clk.value(0)
        self._rst.value(1)

    def _stop(self) -> None:
        self._rst.value(0)

    def _write_byte(self, byte: int) -> None:
        self._dat.init(Pin.OUT)
        for _ in range(8):
            self._dat.value(byte & 0x01)
            byte >>= 1
            self._clk.value(1)
            self._clk.value(0)

    def _read_byte(self) -> int:
        self._dat.init(Pin.IN)
        result = 0
        for i in range(8):
            if self._dat.value():
                result |= (1 << i)
            self._clk.value(1)
            self._clk.value(0)
        return result

    def _write_reg(self, addr: int, value: int) -> None:
        self._start()
        self._write_byte(addr)
        self._write_byte(value)
        self._stop()

    def _read_reg(self, addr: int) -> int:
        self._start()
        self._write_byte(addr)
        value = self._read_byte()
        self._stop()
        return value

    def _burst_read(self) -> list:
        """Read 8 clock registers in a single burst transaction."""
        self._start()
        self._write_byte(0xBF)   # burst read address
        regs = [self._read_byte() for _ in range(8)]
        self._stop()
        return regs

    def _burst_write(self, *regs) -> None:
        """Write up to 8 clock registers in a single burst transaction."""
        self._start()
        self._write_byte(_REG_BURST)
        for byte in regs:
            self._write_byte(byte)
        self._stop()
