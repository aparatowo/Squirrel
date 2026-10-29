# battery_alerts.py - warnings of a low battery: at 15 %, 10 %, 5 % and right before it runs out
#
# A background service, loaded only while the warnings are on (BATTERY_WARN; squirrel_app.py).  Each threshold
# (LEVELS, then the last one: nuts.BATTERY_CRITICAL_PCT or BATTERY_CRITICAL_MV, whichever comes first) is announced
# once, when the level goes down past it: a notification with the sound (BATTERY_WARN_SOUND), the buzzer / vibration
# (BUZZER_BATTERY) and the LED (LED_BATTERY), all of them quiet in the silent hours.  Started below several thresholds (switched on at
# 7 %), only the lowest is announced.  Charging forgets them all; a level that comes back up by REARM_PCT (the ADC's
# reading wanders) makes that threshold count again.  The LED blinks with it as LED_BATTERY says (hw/led.py).
import time
import nuts

LEVELS = (15, 10, 5)
REARM_PCT = 3
_CHECK_MS = 5000


class BatteryAlerts:
    def __init__(self, cfg, monitor, notifier, now_ms=None):
        self._cfg = cfg
        self._monitor = monitor
        self._notifier = notifier
        self._now = now_ms or time.ticks_ms
        self._warned = set()             # thresholds announced since the last charge (0 = the last one)
        self._next = 0

    def tick(self):
        now = self._now()
        if time.ticks_diff(now, self._next) < 0:
            return
        self._next = time.ticks_add(now, _CHECK_MS)
        if not self._cfg.get("BATTERY_WARN"):
            return
        m = self._monitor
        level = m.level_pct
        if m.charging is True:
            self._warned.clear()
            return
        if level is None:
            return
        for t in list(self._warned):
            if t and level >= t + REARM_PCT:
                self._warned.discard(t)
        mv = m.millivolts
        critical = level <= nuts.BATTERY_CRITICAL_PCT or (mv is not None and 0 < mv <= nuts.BATTERY_CRITICAL_MV)
        crossed = [t for t in LEVELS if level <= t] + ([0] if critical else [])
        new = [t for t in crossed if t not in self._warned]
        if not new:
            return
        self._warned.update(crossed)
        self._warn(min(new), level)

    def _warn(self, threshold, level):
        from notifier import Notification
        from i18n import _
        critical = threshold == 0
        text = _("Almost empty - charge it now!") if critical else _("Battery low: %d%%") % level
        self._notifier.post(Notification(
            text, title=_("Battery"), sound="battery" if self._cfg.get("BATTERY_WARN_SOUND") else None,
            timeout_s=20, repeat_s=0, done_label="OK", cancel_label="Close",
            buzzer=("BUZZER_BATTERY", "alarm" if critical else "double"), led="LED_BATTERY"))
