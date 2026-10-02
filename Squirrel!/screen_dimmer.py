# screen_dimmer.py - dims the screen after a period without key presses
#
# Only the back-light changes: the CPU keeps running, so the focus timer, routines and sounds
# carry on.  The key that wakes the screen is swallowed by the main loop (wake() returns True);
# the G0 button wakes the screen AND acts, because it is the quick-recorder button.
# Settings are read live: SCREEN_DIM_SECONDS (0 = never), BRIGHTNESS (0 = keep the device's own),
# DIM_BRIGHTNESS (percent of the normal brightness while dimmed).

import time


class ScreenDimmer:
    def __init__(self, lcd, cfg, can_dim):
        self._lcd = lcd
        self._cfg = cfg
        self._can_dim = can_dim          # function: False while the screen must stay on
        self.dimmed = False
        self._last = time.ticks_ms()
        self._startup = self._read()
        if cfg.get("BRIGHTNESS") > 0:
            self._set(cfg.get("BRIGHTNESS"))
        cfg.on_change(self._on_change)

    def _read(self):
        try:
            value = int(self._lcd.getBrightness())
            return value if value > 0 else None
        except Exception:
            return None

    def _set(self, value):
        try:
            self._lcd.setBrightness(int(value))
        except Exception:
            pass

    def base(self):
        """Normal brightness."""
        configured = self._cfg.get("BRIGHTNESS")
        return configured if configured > 0 else (self._startup or 128)

    def activity(self):
        self._last = time.ticks_ms()

    def wake(self):
        """Note activity and light the screen up.  Returns True if it had been dimmed."""
        self._last = time.ticks_ms()
        if not self.dimmed:
            return False
        self.dimmed = False
        self._set(self.base())
        return True

    def tick(self):
        seconds = self._cfg.get("SCREEN_DIM_SECONDS")
        allowed = seconds > 0 and self._can_dim()
        if self.dimmed:
            if not allowed:
                self.wake()
            return
        if not allowed:
            self._last = time.ticks_ms()               # the idle time starts when dimming is allowed again
            return
        if time.ticks_diff(time.ticks_ms(), self._last) >= seconds * 1000:
            self.dimmed = True
            self._set(self.base() * self._cfg.get("DIM_BRIGHTNESS") // 100)

    def _on_change(self, key, value):
        if key == "BRIGHTNESS" and not self.dimmed:
            self._set(self.base())
        elif key == "DIM_BRIGHTNESS" and self.dimmed:
            self._set(self.base() * value // 100)
        elif key == "SCREEN_DIM_SECONDS":
            self._last = time.ticks_ms()
