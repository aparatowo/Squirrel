# deep_sleep.py - sleeping for real on a device whose hardware clock has an alarm (features.toml: deep_sleep; the watch)
#
# POWER_SLEEP = "deep": after POWER_DEEP_SLEEP_MIN minutes with the screen dimmed and nothing going on, the device
# writes the next alarm (alarms.py: routines, the cuckoo, snoozed routines) into its clock and goes into a deep sleep:
# the panel, the touch screen, the amplifier off; the ESP32 at a few microamps.  The side button or the alarm wakes it -
# the ESP32 then starts from scratch, and on_boot() puts back what was going on (the focus timer counts the time slept,
# snoozed routines are kept) and clears the alarm.  After a wake by the alarm the routine / the cuckoo happens as usual
# (the scheduler checks the current minute at once) and the device goes back to sleep soon (QUICK_S after the screen
# dims), not after the full POWER_DEEP_SLEEP_MIN.
#
# Never while Pomodoro / Training or the metronome run (or are paused), a notification is up, a screen keeps itself on,
# or anything else keeps the app busy (sound, signals, a time sync).
import json
import os
import time
from boot_log import log

QUICK_S = 30                    # after a wake by an alarm: back to sleep this long after the screen dims
_CHECK_MS = 1000
_MIN_LEAD_S = 20                # an event closer than this is waited for awake (the alarm has a one-minute resolution)


class DeepSleep:
    def __init__(self, app, board, cfg, queue, state_path):
        self._app = app
        self._board = board
        self._cfg = cfg
        self._queue = queue
        self._path = state_path
        self._dim_since = None
        self._checked = 0
        self.quick = False               # woken by an alarm: sleep again soon
        self.woke = None                 # "alarm" / "button" / None (not from a deep sleep)

    # ---- at start-up
    def on_boot(self):
        """Put back the state saved before the sleep; disarm the alarm.  Call once the app's parts exist."""
        try:
            self.woke = self._board.wake_reason()
        except Exception:
            self.woke = None
        try:
            chip = self._app.rtc.chip()
            if chip is not None:
                chip.set_alarm(None)                      # releases the INT line; the next sleep writes the next one
        except Exception as e:
            log(f"[SLEEP] cannot clear the clock's alarm: {e}")
        try:
            with open(self._path) as f:
                saved = json.load(f)
            os.remove(self._path)
        except (OSError, ValueError):
            saved = None
        if saved:
            self._app.focus.resume(saved.get("focus"))
            self._app.scheduler.import_snoozes(saved.get("snoozed", []))
        self.quick = self.woke == "alarm"
        if self.woke:
            log(f"[SLEEP] woke up: {self.woke}" + (" (slept %d s)" % (time.time() - saved["at"]) if saved and "at" in saved else ""))

    def user_active(self):
        """A key / touch / button: the user is here - the full delay again."""
        self.quick = False

    # ---- the service
    def _blocked(self):
        app = self._app
        if self._cfg.get("POWER_SLEEP") != "deep":
            return "mode"
        if app.overlay is not None or getattr(app.active_screen, "keeps_screen_on", False):
            return "screen"
        runner = app._runner
        if runner is not None and runner.state in ("running", "paused"):
            return "pomodoro"
        if app._metronome is not None and app._metronome.running:
            return "metronome"
        if app._power_busy():
            return "busy"
        return None

    def tick(self):
        now = time.ticks_ms()
        if time.ticks_diff(now, self._checked) < _CHECK_MS:
            return
        self._checked = now
        if not self._app.dimmer.dimmed:
            self._dim_since = None
            return
        if self._dim_since is None:
            self._dim_since = now
        limit = QUICK_S if self.quick else self._cfg.get("POWER_DEEP_SLEEP_MIN") * 60
        if time.ticks_diff(now, self._dim_since) < limit * 1000 or self._blocked():
            return
        self.sleep_now()

    def next_alarm(self):
        """(epoch, label, (y, m, d, h, mi)) of the alarm the next sleep would set, or None (no events / no clock)."""
        now = time.time()
        if time.localtime(now)[0] < 2024:
            return None
        event = self._queue.next(now)
        if event is None:
            return None
        at = event[0]
        if at % 60:
            at += 60 - at % 60                            # the clock's alarm has minutes only: never early
        t = time.localtime(at)
        return at, event[1], (t[0], t[1], t[2], t[3], t[4])

    def sleep_now(self):
        app = self._app
        alarm = self.next_alarm()
        if alarm is not None and alarm[0] - time.time() < _MIN_LEAD_S:
            return                                        # it is about to happen: stay awake for it
        state = {"at": time.time(), "focus": app.focus.suspend(), "snoozed": app.scheduler.export_snoozes()}
        try:
            with open(self._path, "w") as f:
                json.dump(state, f)
        except OSError as e:
            log(f"[SLEEP] cannot save the state ({e}) - not sleeping")
            app.focus.resume(state["focus"])
            return
        if alarm is None:
            log("[SLEEP] deep sleep; no alarm - the button wakes")
        else:
            t = alarm[2]
            log("[SLEEP] deep sleep; alarm %04d-%02d-%02d %02d:%02d (%s)" % (t[0], t[1], t[2], t[3], t[4], alarm[1]))
        self._board.deep_sleep(None if alarm is None else alarm[2], touch=getattr(app.keypad, "chip", None))
