# ft6336_touch.py - an FT6336U touch controller as the app's input: gestures become the actions a keyboard gives
#
# The screens only know actions ("UP", "ENTER", "ESC" ...).  A gesture is turned into one when it ends:
#   tap          a short touch that hardly moved                       -> actions["tap"]
#   swipe        moved at least SWIPE px, mostly in one direction      -> actions["swipe_up" / "_down" / "_left" / "_right"]
#   long         held LONG_MS without moving (fires while still held)  -> actions["long"]
# The mapping is the board's (ports/<port>/board.py).  Coordinates match the picture (measured on the T-Watch 2020 V3
# with the display rotated 180 degrees): x to the right, y downwards, 0..239.
import time
from boot_log import log

_ADDR = 0x38
SWIPE = 40                    # px
TAP_MOVE = 20                 # px a tap may move
LONG_MS = 600


class FT6336Touch:
    is_text_mode = False
    modifiers_as_keys = False
    display_modifier = None
    last_key_code = 0

    def __init__(self, open_bus, actions, reset=None):
        """open_bus() -> machine.I2C of the touch bus (called again to recover after errors); actions: gesture ->
        action; reset: a callable that pulses the controller's reset line (before first use)."""
        self._open = open_bus
        self.actions = actions
        if reset is not None:
            reset()
        self.i2c = open_bus()
        self._down = False
        self._x0 = self._y0 = self._x = self._y = 0
        self._t0 = 0
        self._long = False
        self._fails = 0
        try:
            log("[TOUCH] FT6x36 chip id 0x%02x" % self.i2c.readfrom_mem(_ADDR, 0xA3, 1)[0])
        except OSError as e:
            log(f"[TOUCH] no answer: {e}")

    def set_text_mode(self, enable):
        self.is_text_mode = enable

    def acknowledge(self):
        return True

    def _point(self):
        d = self.i2c.readfrom_mem(_ADDR, 0x02, 5)
        if not d[0] & 0x0F:
            return None
        return (d[1] & 0x0F) << 8 | d[2], (d[3] & 0x0F) << 8 | d[4]

    def get_pressed_action(self):
        try:
            p = self._point()
            self._fails = 0
        except OSError as e:
            self._fails += 1
            if self._fails <= 5:
                log(f"[TOUCH] read failed (#{self._fails}): {e}")
            try:
                self.i2c = self._open()
            except Exception:
                pass
            return None, False
        now = time.ticks_ms()
        if p is not None:
            if not self._down:
                self._down, self._long = True, False
                self._x0, self._y0 = p
                self._t0 = now
            self._x, self._y = p
            if (not self._long and time.ticks_diff(now, self._t0) >= LONG_MS
                    and abs(self._x - self._x0) < TAP_MOVE and abs(self._y - self._y0) < TAP_MOVE):
                self._long = True
                return self.actions.get("long"), False
            return None, False
        if not self._down:
            return None, False
        self._down = False                            # the finger was lifted: what was it?
        if self._long:
            return None, False
        dx, dy = self._x - self._x0, self._y - self._y0
        if abs(dx) < TAP_MOVE and abs(dy) < TAP_MOVE:
            return self.actions.get("tap"), False
        if abs(dy) >= abs(dx) and abs(dy) >= SWIPE:
            return self.actions.get("swipe_up" if dy < 0 else "swipe_down"), False
        if abs(dx) >= SWIPE:
            return self.actions.get("swipe_left" if dx < 0 else "swipe_right"), False
        return None, False
