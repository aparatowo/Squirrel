# buzzer.py - an extra buzzer on a GPIO, driven through an NPN transistor
#
# Hardware (nuts.py): BUZZER_INSTALLED says whether one is soldered on at all, BUZZER_PIN which GPIO drives the
# transistor's base, BUZZER_PWM_FREQ 0 for an active buzzer (it beeps by itself: plain on / off) or the tone in Hz
# for a passive one (driven with PWM).  The pin is held LOW whenever the buzzer is silent - HIGH = the transistor
# conducts = sound.  A pin of the keyboard's I2C bus is refused: driving it would stop the keyboard.
#
# Which features may use the buzzer is a list of on/off settings (group "Buzzer", all off by default), each with
# a mode (<feature>_MODE): one of MODE_NAMES, or "auto" = the mode the feature passes itself (see nuts.py).
# signal() reads them from the settings in memory (appconfig.cfg), like the rest of the program.
# The silent hours of the buzzer (QUIET_BUZZER_*, Settings -> Silent mode): signal() is wrapped in
# quiet_hours.quiet_guard("buzzer"), and is skipped during them unless force=True.
#
# A signal is played by tick() (a background service), so a long one never stops the program.

import time
import nuts
from boot_log import log
from appconfig import cfg
from quiet_hours import quiet_guard

# Modes: tuples of (on ms, off ms)
MODES = {
    "click":  ((15, 0),),
    "short":  ((80, 0),),
    "double": ((80, 80), (80, 0)),
    "triple": ((60, 60), (60, 60), (60, 0)),
    "long":   ((600, 0),),
    "alarm":  ((150, 100), (150, 100), (150, 100), (150, 0)),
    "sos":    ((80, 80), (80, 80), (80, 200), (250, 80), (250, 80), (250, 200), (80, 80), (80, 80), (80, 0)),
}
MODE_NAMES = ("click", "short", "double", "triple", "long", "alarm", "sos")

# Features that may sound the buzzer, as the names of the settings that allow it (listed in appconfig_schema.py,
# defaults in nuts.py)
FEATURES = (
    "BUZZER_NOTIFY",        # notifications: routines, the end of Pomodoro / Training, the test notification
    "BUZZER_INTERVALS",     # the start of every Pomodoro / Training block
    "BUZZER_METRONOME",     # every metronome beat
    "BUZZER_CUCKOO",        # the cuckoo on the hour (and the quarter ticks, if they are on)
)

# What "auto" sounds like for each feature, when a mode is demonstrated in Personalize (the features themselves choose
# per event: Pomodoro / Training double, triple or long; the metronome short or click; the cuckoo double or click)
AUTO_DEMO = {
    "BUZZER_NOTIFY": "double",
    "BUZZER_INTERVALS": "double",
    "BUZZER_METRONOME": "short",
    "BUZZER_CUCKOO": "double",
}

_I2C_PINS = (nuts.I2C_SDA_PIN, nuts.I2C_SCL_PIN)


class Buzzer:
    def __init__(self):
        self._pin = None
        self._pwm = None
        self._steps = []        # [(on ms, off ms)] still to play
        self._on = False
        self._until = 0
        self.problem = ""       # why the buzzer cannot be used ("" = it can)
        self._quiet = None      # function: True while it must stay silent (a recording runs)

    @property
    def available(self):
        return self._pin is not None

    def status(self):
        """One short line for the screen: "ready, G13" or why it cannot be used."""
        if self._pin is not None:
            return "ready, G%d" % nuts.BUZZER_PIN
        return self.problem or "not started"

    @property
    def busy(self):
        return self._on or bool(self._steps)

    def begin(self, quiet=None):
        """Take the pin and hold it LOW.  Call once, as early as possible."""
        self._quiet = quiet
        if not getattr(nuts, "BUZZER_INSTALLED", False):
            self.problem = "No buzzer (nuts.py)"
            return False
        number = nuts.BUZZER_PIN
        if number in _I2C_PINS:
            self.problem = "G%d is the keyboard bus" % number
            log(f"[BUZZER] G{number} is a pin of the keyboard's I2C bus - not used, move the buzzer to a free GPIO")
            return False
        try:
            from machine import Pin
            self._pin = Pin(number, Pin.OUT, value=0)
            self._pin.value(0)
            if nuts.BUZZER_PWM_FREQ:
                from machine import PWM
                self._pwm = PWM(self._pin, freq=nuts.BUZZER_PWM_FREQ, duty_u16=0)
            log(f"[BUZZER] ready on G{number} ({'PWM %d Hz' % nuts.BUZZER_PWM_FREQ if self._pwm else 'on/off'})")
            return True
        except Exception as e:
            self._pin = self._pwm = None
            self.problem = "Pin error"
            log(f"[BUZZER] cannot use G{number}: {e}")
            return False

    @quiet_guard("buzzer")
    def signal(self, feature, mode="short"):
        """Sound the buzzer if it is there and the settings allow `feature` (see FEATURES), in the mode set for it
        (<feature>_MODE); `mode` is the feature's own choice, used when that setting is "auto".

        Returns True when the signal was started.  A new signal replaces the one still playing.
        Skipped during the buzzer's silent hours, unless called with force=True."""
        if self._pin is None or feature not in FEATURES:
            return False
        if not cfg.get(feature):
            return False
        chosen = cfg.get(feature + "_MODE")
        return self.play(mode if chosen == "auto" else chosen)

    def play(self, mode="short"):
        """Sound `mode` whatever the settings say (the test entries of the Buzzer menu)."""
        if self._pin is None:
            return False
        if self._quiet is not None:
            try:
                if self._quiet():
                    return False
            except Exception:
                pass
        steps = MODES.get(mode)
        if steps is None:
            log(f"[BUZZER] unknown mode {mode!r}")
            return False
        self._set(False)                       # a signal still sounding is cut off
        self._steps = list(steps)
        self._next(time.ticks_ms())
        return True

    def demo(self, feature, mode):
        """Let the user hear `mode` just chosen for `feature` (Personalize); "auto" plays the feature's usual signal.
        Played whatever the settings and the quiet hours say: the user has just asked for it."""
        return self.play(AUTO_DEMO.get(feature, "short") if mode == "auto" else mode)

    def off(self):
        """Silence now and forget the rest of the signal."""
        self._steps = []
        self._set(False)

    def tick(self):
        """Service hook: switch the buzzer on / off on time."""
        if not self.busy:
            return
        now = time.ticks_ms()
        if time.ticks_diff(now, self._until) >= 0:
            self._next(now)

    def _next(self, now):
        """Go on to the next half of the signal: sound -> pause -> next sound ... -> silent."""
        if self._on:
            off_ms = self._steps.pop(0)[1] if self._steps else 0
            self._set(False)
            self._until = time.ticks_add(now, off_ms)
        elif self._steps:
            self._set(True)
            self._until = time.ticks_add(now, self._steps[0][0])
        else:
            self._set(False)

    def _set(self, on):
        self._on = on
        try:
            if self._pwm is not None:
                self._pwm.duty_u16(32768 if on else 0)
            elif self._pin is not None:
                self._pin.value(1 if on else 0)
        except Exception as e:
            log(f"[BUZZER] {e}")


# The one shared instance.  SquirrelApp calls begin() first thing and ticks it as a service.
buzzer = Buzzer()


def signal(feature, mode="short", force=False):
    """Shortcut: buzzer.signal(feature, mode); force=True sounds during the silent hours too."""
    if not buzzer.available:
        return False
    return buzzer.signal(feature, mode, force=force)
