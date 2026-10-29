# hourglass.py - the hourglass: a plain countdown timer (Focus tools -> Hourglass), a background service
#
# States: idle -> running <-> paused -> done -> idle.  Time is counted from time.ticks_ms() (it runs on through a light
# sleep), so it does not depend on the clock being set.  When it runs out, a notification rings - the "alarm" sound,
# the buzzer / vibration (BUZZER_HOURGLASS) and the LED (LED_HOURGLASS) - every few seconds until it is answered, also
# during the silent hours: the hourglass was set by hand, like the metronome.  Answering it (or its timeout) makes the
# hourglass idle again.
# The top bar of the clock follows it (bars.py, BARS_TOP = "hourglass"); the screen is screens/hourglass_screen.py.
# Loaded when first needed (SquirrelApp.hourglass()); a deep sleep waits while it is not idle (deep_sleep.py).
import time

_RING_S = 60                    # how long the alarm rings unanswered
_REPEAT_S = 3                   # ... repeated this often


class Hourglass:
    def __init__(self, notifier, now_ms=None):
        self._notifier = notifier
        self._now = now_ms or time.ticks_ms
        self.state = "idle"            # idle | running | paused | done
        self.total_s = 0
        self._elapsed = 0              # ms counted so far
        self._last = 0

    def start(self, seconds):
        self.total_s = max(1, int(seconds))
        self._elapsed, self._last = 0, self._now()
        self.state = "running"

    def toggle(self):
        """Pause / resume."""
        if self.state == "running":
            self._account()
            self.state = "paused"
        elif self.state == "paused":
            self._last = self._now()
            self.state = "running"

    def stop(self):
        self.state = "idle"

    def _account(self):
        now = self._now()
        self._elapsed += time.ticks_diff(now, self._last)
        self._last = now

    def tick(self):
        if self.state != "running":
            return
        self._account()
        if self._elapsed >= self.total_s * 1000:
            self._elapsed = self.total_s * 1000
            self._finish()

    def _finish(self):
        self.state = "done"
        from notifier import Notification
        from i18n import _
        self._notifier.post(Notification(_("Time is up!"), title=_("Hourglass"), sound="alarm", timeout_s=_RING_S,
                                         repeat_s=_REPEAT_S, on_done=self.stop, on_cancel=self.stop,
                                         on_timeout=self.stop, done_label="OK", cancel_label="Close",
                                         buzzer=("BUZZER_HOURGLASS", "alarm"), led="LED_HOURGLASS", force=True))

    # ---- what the screen and the bar show ----
    def remaining(self):
        """Whole seconds left (rounded up)."""
        if self.state == "idle":
            return 0
        left = self.total_s * 1000 - self._elapsed
        if self.state == "running":
            left -= time.ticks_diff(self._now(), self._last)
        return max(0, (left + 999) // 1000)

    def elapsed_ms(self):
        """Milliseconds counted so far (up to the total)."""
        if self.state == "idle":
            return 0
        elapsed = self._elapsed + (time.ticks_diff(self._now(), self._last) if self.state == "running" else 0)
        return min(elapsed, self.total_s * 1000)
