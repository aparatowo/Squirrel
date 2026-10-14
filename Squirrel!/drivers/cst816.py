# cst816.py - the CST816S / CST816T touch controller (common in ESP32-S3 watches): where the finger is, nothing more
#
# The chip driver of the touch layer, like drivers/ft6336.py: read_point() -> (x, y) in the panel's own coordinates,
# or None; gestures and actions are hw/touch_input.py's.  The chip's own gesture register is not used (the touch
# layer works them out the same way on every chip).  The CST816 puts itself to sleep after a while without a touch
# and does not answer on the bus then: that reads as "no finger", not as an error.
from boot_log import log

ADDR = 0x15
_REG_DATA = 0x01                 # gesture, points, x high (4 bits), x low, y high (4 bits), y low
_REG_CHIP_ID = 0xA7
_REG_SLEEP = 0xE5                # 0x03: deep sleep (a reset wakes it)
_REG_AUTO_SLEEP = 0xFE           # non-zero: no auto sleep (it then answers at once, for a little more current)


class CST816:
    def __init__(self, open_bus, reset=None, addr=ADDR, keep_awake=False):
        """open_bus() -> machine.I2C of the touch bus (called again by reopen() after errors); reset: a callable that
        pulses the controller's reset line (before first use); keep_awake: switch the chip's auto sleep off."""
        self._open = open_bus
        self._addr = addr
        if reset is not None:
            reset()
        self.i2c = open_bus()
        try:
            log("[TOUCH] CST816 chip id 0x%02x" % self.i2c.readfrom_mem(addr, _REG_CHIP_ID, 1)[0])
            if keep_awake:
                self.i2c.writeto_mem(addr, _REG_AUTO_SLEEP, b"\x01")
        except OSError as e:
            log(f"[TOUCH] no answer (asleep until touched?): {e}")

    def read_point(self):
        """(x, y) of the touch point, or None (no finger, or the chip asleep)."""
        try:
            d = self.i2c.readfrom_mem(self._addr, _REG_DATA, 6)
        except OSError:
            return None
        if not d[1] & 0x0F:
            return None
        return (d[2] & 0x0F) << 8 | d[3], (d[4] & 0x0F) << 8 | d[5]

    def reopen(self):
        self.i2c = self._open()

    def hibernate(self):
        """The lowest power mode (before a deep sleep); a reset wakes it."""
        try:
            self.i2c.writeto_mem(self._addr, _REG_SLEEP, b"\x03")
        except OSError:
            pass
