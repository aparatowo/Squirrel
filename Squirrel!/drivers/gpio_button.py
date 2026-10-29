# gpio_button.py - debounced polling of a button wired straight to a GPIO
#
# The Cardputer's G0 (BTN0) is active-low with a pull-up.  pressed() reports each
# physical press exactly once - on the debounced falling edge - so holding the button
# or contact bounce never produces extra events.
# A light sleep stops the polling for ~800 ms: a gap like that starts the debouncing over (and sets the pin up again),
# so one stray low sample before a sleep and one right after the wake no longer add up to a "press" - on the
# Cardputer ADV that started the quick recorder by itself (2026-10-21).

import time
from machine import Pin


_GAP_MS = 400                   # polls further apart: the loop was not running (a light sleep: ~800 ms; a slow pass
                                # of the loop - the clock redrawn - takes ~150 ms)
_AFTER_GAP_MS = 120             # ... and then a press must last this much longer before it counts


class ButtonPoller:
    def __init__(self, pin_no=0, debounce_ms=30):
        self._no = pin_no
        self._pin = Pin(pin_no, Pin.IN, Pin.PULL_UP)
        self._debounce = debounce_ms
        # Start from the real state: a button already held at start-up is not a press.
        self._raw = self._down = (self._pin.value() == 0)
        self._since = self._polled = time.ticks_ms()

    def pressed(self):
        """True once per physical press.  Call every main-loop iteration."""
        now = time.ticks_ms()
        gap = time.ticks_diff(now, self._polled) > _GAP_MS
        self._polled = now
        if gap:
            self._pin = Pin(self._no, Pin.IN, Pin.PULL_UP)    # as it was before the sleep
        raw = (self._pin.value() == 0)
        if gap or raw != self._raw:          # level changed (or not watched for a while): restart the settling timer
            self._raw = raw
            self._since = time.ticks_add(now, _AFTER_GAP_MS) if gap else now    # a pad just woken settles first
            return False
        if raw != self._down and time.ticks_diff(now, self._since) >= self._debounce:
            self._down = raw                 # level has been stable long enough
            return raw                       # only the press counts, not the release
        return False
