# buttons.py - debounced polling of the hardware buttons wired straight to GPIOs
#
# The Cardputer's G0 (BTN0) is active-low with a pull-up.  pressed() reports each
# physical press exactly once - on the debounced falling edge - so holding the button
# or contact bounce never produces extra events.

import time
from machine import Pin


class ButtonPoller:
    def __init__(self, pin_no=0, debounce_ms=30):
        self._pin = Pin(pin_no, Pin.IN, Pin.PULL_UP)
        self._debounce = debounce_ms
        # Start from the real state: a button already held at start-up is not a press.
        self._raw = self._down = (self._pin.value() == 0)
        self._since = time.ticks_ms()

    def pressed(self):
        """True once per physical press.  Call every main-loop iteration."""
        now = time.ticks_ms()
        raw = (self._pin.value() == 0)
        if raw != self._raw:                 # level changed: restart the settling timer
            self._raw = raw
            self._since = now
            return False
        if raw != self._down and time.ticks_diff(now, self._since) >= self._debounce:
            self._down = raw                 # level has been stable long enough
            return raw                       # only the press counts, not the release
        return False
