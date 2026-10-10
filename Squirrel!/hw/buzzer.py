# buzzer.py - an extra buzzer on a GPIO, driven through an NPN transistor
#
# Hardware: the port says whether one is soldered on at all and where ([signal.buzzer] in ports/<port>/port.toml):
# the pin that drives the transistor's base, pwm_freq 0 for an active buzzer (it beeps by itself: plain on / off) or
# the tone in Hz for a passive one (driven with PWM).  The pin is switched by drivers/pin_pulser.py and held LOW
# whenever the buzzer is silent - HIGH = the transistor conducts = sound.  A pin of the I2C bus (the board's
# `reserved` pins) is refused: driving it would stop the keyboard.
#
# Which features may use the buzzer is a list of on/off settings (group "Buzzer", all off by default), each with
# a mode (<feature>_MODE): one of MODE_NAMES, or "auto" = the mode the feature passes itself (see nuts.py).
# signal() reads them from the settings in memory (appconfig.cfg), like the rest of the program.
# The silent hours of the buzzer (QUIET_BUZZER_*, Settings -> Silent mode): signal() is wrapped in
# quiet_hours.quiet_guard("buzzer"), and is skipped during them unless force=True.
#
# A signal is played by tick() (a background service), so a long one never stops the program.

import time
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

class Buzzer:
    def __init__(self):
        self._pin = None        # the PinPulser, once begin() has taken the pin
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
            return "ready, G%d" % self._pin.pin_no
        return self.problem or "not started"

    @property
    def busy(self):
        return self._on or bool(self._steps)

    def begin(self, quiet=None, pin=None, pwm_freq=0, reserved=(), pulser=None):
        """Take the pin and hold it LOW.  Call once, as early as possible.

        pin None = the device has no buzzer.  pulser: the class that drives the pin (drivers/pin_pulser.py), given by
        the board; reserved: pins it must never drive (the I2C bus)."""
        self._quiet = quiet
        if pin is None or pulser is None:
            self.problem = "No buzzer (port.toml)"
            return False
        number = pin
        if number in reserved:
            self.problem = "G%d is the keyboard bus" % number
            log(f"[BUZZER] G{number} is a pin of the keyboard's I2C bus - not used, move the buzzer to a free GPIO")
            return False
        try:
            self._pin = pulser(number, pwm_freq)
            log(f"[BUZZER] ready on G{number} ({'PWM %d Hz' % pwm_freq if self._pin.pwm else 'on/off'})")
            return True
        except Exception as e:
            self._pin = None
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
            if self._pin is not None:
                self._pin.set(on)
        except Exception as e:
            log(f"[BUZZER] {e}")


# The one shared instance.  SquirrelApp calls begin() first thing and ticks it as a service.
buzzer = Buzzer()


def signal(feature, mode="short", force=False):
    """Shortcut: buzzer.signal(feature, mode); force=True sounds during the silent hours too."""
    if not buzzer.available:
        return False
    return buzzer.signal(feature, mode, force=force)
