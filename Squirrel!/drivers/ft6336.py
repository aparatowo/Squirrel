# ft6336.py - the FT6336U touch controller (T-Watch 2020): where the finger is, nothing more
#
# The chip driver of the touch layer: read_point() -> (x, y) in the panel's own coordinates, or None.  Gestures, the
# mapping onto the picture and the actions are the job of hw/touch_input.py - the same for every touch chip, so another
# watch (another controller) needs only its own read_point().
from boot_log import log

_ADDR = 0x38


class FT6336:
    def __init__(self, open_bus, reset=None):
        """open_bus() -> machine.I2C of the touch bus (called again by reopen() after errors); reset: a callable that
        pulses the controller's reset line (before first use)."""
        self._open = open_bus
        if reset is not None:
            reset()
        self.i2c = open_bus()
        try:
            log("[TOUCH] FT6x36 chip id 0x%02x" % self.i2c.readfrom_mem(_ADDR, 0xA3, 1)[0])
        except OSError as e:
            log(f"[TOUCH] no answer: {e}")

    def read_point(self):
        """(x, y) of the first touch point, or None.  Raises OSError when the bus fails."""
        d = self.i2c.readfrom_mem(_ADDR, 0x02, 5)
        if not d[0] & 0x0F:
            return None
        return (d[1] & 0x0F) << 8 | d[2], (d[3] & 0x0F) << 8 | d[4]

    def reopen(self):
        self.i2c = self._open()
