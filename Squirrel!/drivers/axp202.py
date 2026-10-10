# axp202.py - the AXP202 power chip (T-Watch 2020): the supplies, the battery, the side button (its power key)
#
# Facts measured on the T-Watch 2020 V3 (tools/hwtest/README_PL.md): LDO2 = the display and its backlight; LDO4 = the
# audio amplifier, at 3.3 V (LilyGo's library sets it so; it may come up at 1.8 V); LDO3 is unused; DCDC3 / DCDC2 feed
# the ESP32 itself and are never touched here.  A pending interrupt holds the INT line low until its flag is cleared.
#
# As a power source (hw/battery.py) it offers level(), charging(), millivolts(); as the side button, short_press() /
# long_press() (drivers/axp_pek.py makes a button of them).

_ADDR = 0x35
_LDO2, _LDO4 = 0x04, 0x08                       # bits of register 0x12
_LDO4_3300 = 0x0F                               # low nibble of register 0x28


class AXP202:
    def __init__(self, i2c):
        self.i2c = i2c
        self._pek = 0                           # power-key flags read but not handed out yet (bit 1 short, bit 0 long)

    def _r(self, reg):
        return self.i2c.readfrom_mem(_ADDR, reg, 1)[0]

    def _w(self, reg, v):
        self.i2c.writeto_mem(_ADDR, reg, bytes([v & 0xFF]))

    def chip_ok(self):
        try:
            return self._r(0x03) == 0x41
        except OSError:
            return False

    def begin(self):
        """At start-up: display power on, the ADCs on, the power-key interrupts on, every stale interrupt cleared."""
        if 1.8 + 0.1 * (self._r(0x28) >> 4) < 3.0:
            self._w(0x28, (self._r(0x28) & 0x0F) | 0xF0)          # LDO2 3.3 V (LilyGo's setting)
        self._w(0x12, self._r(0x12) | _LDO2)
        self._w(0x82, self._r(0x82) | 0xCC)                      # battery voltage + current, VBUS voltage + current
        # IRQs: only the power key (short / long press).  The INT line wakes the watch from a deep sleep, so nothing
        # else may pull it (charging finished, USB plugged ...) - it would wake the watch again and again.
        for reg, value in ((0x40, 0), (0x41, 0), (0x42, 0x03), (0x43, 0), (0x44, 0)):
            self._w(reg, value)
        self.clear_irqs()

    def clear_irqs(self):
        """Clear every pending interrupt flag: the INT line goes high again."""
        for reg in range(0x48, 0x4D):
            self._w(reg, 0xFF)                                   # write 1 = clear
        self._pek = 0

    def audio_power(self, on):
        """The amplifier's supply: LDO4 at 3.3 V (LilyGo: off, set the voltage, on)."""
        out = self._r(0x12)
        if on:
            if self._r(0x28) & 0x0F != _LDO4_3300:
                self._w(0x12, out & ~_LDO4)
                self._w(0x28, (self._r(0x28) & 0xF0) | _LDO4_3300)
            self._w(0x12, self._r(0x12) | _LDO4)
        else:
            self._w(0x12, out & ~_LDO4)

    def display_power(self, on):
        out = self._r(0x12)
        self._w(0x12, (out | _LDO2) if on else (out & ~_LDO2))

    # ---- the power source of hw/battery.py
    def millivolts(self):
        try:
            return int((self._r(0x78) << 4 | (self._r(0x79) & 0x0F)) * 1.1)
        except OSError:
            return None

    def level(self):
        """Battery level 0..100 from the chip's fuel gauge, or None."""
        try:
            if not self._r(0x01) & 0x20:                         # no battery
                return None
            v = self._r(0xB9) & 0x7F
            return v if v <= 100 else None
        except OSError:
            return None

    def charging(self):
        try:
            return bool(self._r(0x01) & 0x40)
        except OSError:
            return None

    # ---- the side button
    def _poll_pek(self):
        st = self._r(0x4A) & 0x03
        if st:
            self._w(0x4A, st)                                    # clear what was read
            self._pek |= st

    def short_press(self):
        self._poll_pek()
        if self._pek & 0x02:
            self._pek &= ~0x02
            return True
        return False

    def long_press(self):
        self._poll_pek()
        if self._pek & 0x01:
            self._pek &= ~0x01
            return True
        return False
