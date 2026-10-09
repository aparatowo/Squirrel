# screen_dimmer.py - dims the screen after a period without key presses
#
# Only the back-light changes: the CPU keeps running, so the focus timer, routines and sounds
# carry on.  The key that wakes the screen is swallowed by the main loop (wake() returns True);
# the G0 button wakes the screen AND acts, because it is the quick-recorder button.
# Settings are read live: SCREEN_DIM_CLOCK_SECONDS on the main screen and SCREEN_DIM_OTHER_SECONDS everywhere else
# (0 = never), BRIGHTNESS (0 = keep the device's own), DIM_BRIGHTNESS (percent of the normal brightness while dimmed).
#
# A floor: on the Cardputer ADV the RGB LED gets its power through the back-light's switched (PWM) supply - below a
# back-light of about 200 it resets after a flash, at 0 it is dead (measured, see nuts.LED_MIN_BACKLIGHT).  So while the
# LED has something to show, `floor()` returns that minimum and the back-light is kept at least that bright, dimmed or
# not; the intended brightness comes back as soon as the LED is dark again.

import time


class ScreenDimmer:
    def __init__(self, lcd, cfg, can_dim, on_main=None, on_wake=None, floor=None):
        self._lcd = lcd
        self._cfg = cfg
        self._can_dim = can_dim          # function: False while the screen must stay on
        self._on_main = on_main          # function: True while the main screen (the clock) is shown
        self._on_wake = on_wake          # function called when a dimmed screen lights up again
        self._floor = floor              # function: the lowest back-light allowed right now (0 = no limit)
        self.dimmed = False
        self._last = time.ticks_ms()
        self._startup = self._read()
        self._level = self.base()        # the brightness wanted (normal or dimmed), before the floor
        self._applied = self._startup    # what the back-light was last set to
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
        """Make `value` the wanted brightness; the back-light gets it, or the floor if that is higher."""
        self._level = int(value)
        self._apply()

    def _apply(self):
        value = self._level
        if self._floor is not None:
            try:
                value = max(value, int(self._floor()))
            except Exception:
                pass
        if value == self._applied:
            return
        self._applied = value
        try:
            self._lcd.setBrightness(value)
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
        if self._on_wake is not None:
            try:
                self._on_wake()
            except Exception:
                pass
        return True

    def tick(self):
        self._apply()                                  # the floor may have changed (the LED lit up or went dark)
        main = self._on_main is not None and self._on_main()
        seconds = self._cfg.get("SCREEN_DIM_CLOCK_SECONDS" if main else "SCREEN_DIM_OTHER_SECONDS")
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
        elif key in ("SCREEN_DIM_CLOCK_SECONDS", "SCREEN_DIM_OTHER_SECONDS"):
            self._last = time.ticks_ms()
