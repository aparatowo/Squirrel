# touch_input.py - a touch screen as the app's input, whatever the touch chip (the chip driver gives read_point())
#
# The screens only know actions ("UP", "ENTER", "ESC" ...).  A gesture becomes one when it ends:
#   tap          a short touch that hardly moved                       -> actions["tap"]
#   swipe        moved far enough, mostly in one direction             -> actions["swipe_up" / "_down" / "_left" / "_right"]
#   long         held without moving (fires while still held)          -> actions["long"]
# The mapping is the port's (ports/<port>/board.py).  Distances are in millimetres (the port's pixels per mm), so a
# finger does the same on a denser screen.
#
# A screen made for touch may also look WHERE (ui/touch.py does): touch_xy is the point while a finger is down (else
# None), tap_xy the point of the last tap / long press - in the coordinates the screens draw in.  The chip's own
# coordinates are turned into those by the port's transform (swap / mirror, [input] in port.toml) and by the origin of
# the layout area (origin(): the y where it starts on the panel - it moves when a screen uses the full height).
import time
from boot_log import log

TAP_MOVE_MM = 2.5             # a tap may move this much
SWIPE_MM = 4.5                # a swipe moves at least this much
LONG_MS = 600


class TouchInput:
    is_text_mode = False
    modifiers_as_keys = False
    display_modifier = None
    last_key_code = 0
    touch = True                       # ui/touch.py: this input can say where

    def __init__(self, chip, actions, size=(240, 240), px_per_mm=8.0, swap_xy=False, mirror_x=False, mirror_y=False,
                 origin=None):
        self.chip = chip
        self.actions = actions
        self._w, self._h = size
        self._swap, self._mx, self._my = swap_xy, mirror_x, mirror_y
        self._origin = origin or (lambda: 0)
        self._tap = TAP_MOVE_MM * px_per_mm
        self._swipe = SWIPE_MM * px_per_mm
        self.touch_xy = None
        self.tap_xy = None
        self._down = self._long = False
        self._x0 = self._y0 = self._x = self._y = 0
        self._t0 = 0
        self._fails = 0
        self.i2c = getattr(chip, "i2c", None)

    def set_text_mode(self, enable):
        self.is_text_mode = enable

    def acknowledge(self):
        return True

    def _map(self, p):
        """The chip's point -> the picture's (x right, y down, 0..size-1), before the layout origin."""
        x, y = p
        if self._swap:
            x, y = y, x
        if self._mx:
            x = self._w - 1 - x
        if self._my:
            y = self._h - 1 - y
        return x, y

    def get_pressed_action(self):
        try:
            p = self.chip.read_point()
            self._fails = 0
        except OSError as e:
            self._fails += 1
            if self._fails <= 5:
                log(f"[TOUCH] read failed (#{self._fails}): {e}")
            try:
                self.chip.reopen()
            except Exception:
                pass
            return None, False
        now = time.ticks_ms()
        oy = self._origin()
        if p is None:
            self.touch_xy = None
        else:
            p = self._map(p)
            self.touch_xy = (p[0], p[1] - oy)
            if not self._down:
                self._down, self._long = True, False
                self._x0, self._y0 = p
                self._t0 = now
            self._x, self._y = p
            if (not self._long and time.ticks_diff(now, self._t0) >= LONG_MS
                    and abs(self._x - self._x0) < self._tap and abs(self._y - self._y0) < self._tap):
                self._long = True
                self.tap_xy = (self._x0, self._y0 - oy)
                return self.actions.get("long"), False
            return None, False
        if not self._down:
            return None, False
        self._down = False                            # the finger was lifted: what was it?
        if self._long:
            return None, False
        dx, dy = self._x - self._x0, self._y - self._y0
        if abs(dx) < self._tap and abs(dy) < self._tap:
            self.tap_xy = (self._x0, self._y0 - oy)
            return self.actions.get("tap"), False
        if abs(dy) >= abs(dx) and abs(dy) >= self._swipe:
            return self.actions.get("swipe_up" if dy < 0 else "swipe_down"), False
        if abs(dx) >= self._swipe:
            return self.actions.get("swipe_left" if dx < 0 else "swipe_right"), False
        return None, False
