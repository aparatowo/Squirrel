# battery.py - battery level, read every now and then in the background
#
# Where the numbers come from is the port's: the board gives level(), charging() and millivolts() (on the Cardputer
# drivers/m5_power.py; each returns None when it cannot tell), and maybe usb_host().
#
# Charging.  The watch's power chip says it (drivers/axp202.py).  The Cardputers cannot: their battery is only measured
# through the ADC, the charger's status pins go to its LED, not to the ESP32, and the ESP32-S3 cannot see a USB supply
# without data (it has no VBUS pin - only a host's frames show).  For them there is a guess (the setting CHARGE_GUESS,
# Settings -> Experimental): ChargeGuess below, from the voltage and - when a computer is on the USB - its frames.

import time


def _unknown():
    return None


_GUESS_MS = 10000               # the poll while guessing: the voltage is followed more closely


class ChargeGuess:
    """Charging guessed from the battery voltage, read every few seconds.

    A charger lifts the battery's voltage at once (its current through the cell's resistance) and lets it fall when it
    goes: a jump of STEP_MV or more that is still there at the next reading says "plugged in" / "unplugged".  A slow
    rise of RISE_MV within WINDOW readings says "charging" too (a nearly full battery takes little current - no jump);
    a slow fall of FALL_MV says it is not.  A computer's frames on the USB (usb=True) say it at once.  Load changes (the
    radio, the speaker) make jumps too, but brief ones: they are gone at the next reading."""
    STEP_MV = 60
    RISE_MV = 20
    FALL_MV = 15
    WINDOW = 30                  # readings: 5 minutes at one every 10 s
    PLUGGED_MV = 4200            # at start-up: a battery above this is on a charger (it rests lower)

    def __init__(self):
        self.charging = None     # True / False; None before the first reading
        self._history = []       # the last WINDOW readings, mV
        self._jump = 0           # +1 / -1: a jump was seen at the last reading and waits to be confirmed

    def feed(self, mv, usb=None):
        if usb:
            self.charging = True
        if mv is None:
            return self.charging
        h = self._history
        if self.charging is None:
            self.charging = mv >= self.PLUGGED_MV
        if h:
            d = mv - h[-1]
            if self._jump and (mv - h[-2] if len(h) > 1 else d) * self._jump >= self.STEP_MV * 2 // 3:
                self.charging = self._jump > 0          # the jump is still there: the charger came / went
                self._jump = 0
                del h[:-1]                              # the trend starts again from here
            else:
                self._jump = 1 if d >= self.STEP_MV else (-1 if d <= -self.STEP_MV else 0)
        h.append(mv)
        del h[:-self.WINDOW]
        if len(h) == self.WINDOW and not self._jump:
            early = (h[0] + h[1] + h[2]) // 3
            late = (h[-1] + h[-2] + h[-3]) // 3
            if late - early >= self.RISE_MV:
                self.charging = True
            elif early - late >= self.FALL_MV and not usb:
                self.charging = False
        return self.charging


class BatteryMonitor:
    """Service: polls the fuel gauge every `interval_ms`.  level() is None when it cannot be read.

    charging: True / False, or None when the device cannot tell - unless guess() is true (CHARGE_GUESS): then the
    guess (charging_guessed = True).  millivolts: the last voltage read, or None."""

    def __init__(self, read=None, charging=None, interval_ms=30000, millivolts=None, usb_host=None, guess=None):
        self._read = read or _unknown
        self._charging = charging or _unknown
        self._mv = millivolts or _unknown
        self._usb = usb_host or _unknown
        self._guess_on = guess or (lambda: False)
        self._guess = None           # a ChargeGuess while guessing
        self._interval = interval_ms
        self.level_pct = None
        self.charging = None             # True / False, or None: this device cannot tell
        self.charging_guessed = False
        self.millivolts = None
        self._next = 0
        self._poll()

    def level(self):
        return self.level_pct

    def tick(self):
        if time.ticks_diff(time.ticks_ms(), self._next) >= 0:
            self._poll()

    def _poll(self):
        try:
            value = self._read()
        except Exception:
            value = None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or value > 100:
            self.level_pct = None
        else:
            self.level_pct = int(value)
        try:
            self.millivolts = self._mv()
        except Exception:
            self.millivolts = None
        try:
            value = self._charging()
            self.charging = None if value is None else bool(value)
        except Exception:
            self.charging = None
        guessing = False
        if self.charging is None:
            try:
                guessing = bool(self._guess_on())
            except Exception:
                pass
        if guessing:
            if self._guess is None:
                self._guess = ChargeGuess()
            try:
                usb = self._usb()
            except Exception:
                usb = None
            self.charging = self._guess.feed(self.millivolts, usb)
        else:
            self._guess = None
        self.charging_guessed = guessing
        self._next = time.ticks_add(time.ticks_ms(), _GUESS_MS if guessing else self._interval)


HEADER = "time,level_pct,charging,mv,screen,mode,dim_s,slowcpu_s,sleeps,led_s,speaker_s,radio_s"
_SAMPLE_MS = 1000                # how often the states are looked at between two lines


class BatteryLogger:
    """Service, on by default (BATTERY_LOG): one line every 10 minutes in a CSV on the SD card.

    The data is for developing the power features (an ultra power-saving mode, a calmer screen): it shows how the
    battery goes down and what was running meanwhile.  It stays on the card - nothing is ever sent anywhere.
    Columns: time (local, or uptime if the clock is not set), level %, charging 0/1 (empty: the device cannot tell),
    mV, screen on/off and the power mode set (at the moment of the line), then for the 10 minutes before the line:
    seconds with the screen dimmed, with the CPU slowed down, light sleeps, seconds the LED needed the back-light,
    seconds the speaker was on, seconds the radio was in use.
    Light on purpose (the logger must not be what drains the battery): the states are looked at once a second (a few
    attribute reads), one append every 10 minutes; the folder and the header are dealt with once, on the first write."""

    def __init__(self, cfg, monitor, dimmer, path, interval_ms=600000, now_ms=None, localtime=None, voltage=None):
        self._cfg = cfg
        self._monitor = monitor
        self._dimmer = dimmer
        self._path = path
        self._interval = interval_ms
        self._now = now_ms or time.ticks_ms
        self._localtime = localtime or time.localtime
        self._voltage = voltage or _unknown
        self._next = 0
        self._ready = False              # folder made and header written (checked once)
        self._probes = (lambda: dimmer.dimmed,)    # what is timed: functions returning True / False (see attach)
        self._sleeps = None              # function: light sleeps since start-up
        self._acc = [0]                  # ms each probe was True since the last line
        self._sleeps_at = 0
        self._sampled = None             # when the probes were last looked at

    def attach(self, slow, led, speaker, radio, sleeps):
        """The other states to time (functions returning True / False) and the light-sleep counter - given once the app
        has built the parts they come from."""
        dimmer = self._dimmer
        self._probes = (lambda: dimmer.dimmed, slow, led, speaker, radio)
        self._acc = [0] * len(self._probes)
        self._sleeps = sleeps
        self._sleeps_at = self._count_sleeps()

    def _count_sleeps(self):
        try:
            return int(self._sleeps()) if self._sleeps is not None else 0
        except Exception:
            return 0

    def _sample(self, now):
        if self._sampled is None:
            self._sampled = now
            return
        dt = time.ticks_diff(now, self._sampled)
        if dt < _SAMPLE_MS:
            return
        self._sampled = now
        for i, probe in enumerate(self._probes):
            try:
                if probe():
                    self._acc[i] += dt
            except Exception:
                pass

    def tick(self):
        if not self._cfg.get("BATTERY_LOG"):
            self._sampled = None
            return
        now = self._now()
        self._sample(now)
        if time.ticks_diff(now, self._next) < 0:
            return
        self._next = time.ticks_add(now, self._interval)
        t = self._localtime()
        stamp = "%04d-%02d-%02d %02d:%02d" % (t[0], t[1], t[2], t[3], t[4]) if t[0] >= 2024 else "up%ds" % (now // 1000)
        sleep = self._cfg.get("POWER_SLEEP")
        mode = (sleep + "sleep") if sleep != "off" else ("slowcpu" if self._cfg.get("POWER_SAVE") else "full")
        level = self._monitor.level()
        charging = self._monitor.charging
        timed = [ms // 1000 for ms in self._acc] + [0] * (5 - len(self._acc))
        sleeps = self._count_sleeps()
        line = "%s,%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d\n" % (
            stamp, "" if level is None else level, "" if charging is None else int(charging),
            self._voltage() or "", "off" if self._dimmer.dimmed else "on", mode,
            timed[0], timed[1], sleeps - self._sleeps_at, timed[2], timed[3], timed[4])
        self._acc = [0] * len(self._acc)
        self._sleeps_at = sleeps
        try:
            if not self._ready:
                self._prepare()
            with open(self._path, "a") as f:
                f.write(line)
        except OSError:
            self._ready = False          # the card was away: check the folder and the header again next time

    def _prepare(self):
        """The folder, and a file that starts with this version's header (an older file is kept as .old.csv)."""
        import os
        folder = self._path.rpartition("/")[0]
        try:
            os.mkdir(folder)
        except OSError:
            pass
        first = None
        try:
            with open(self._path) as f:
                first = f.readline().strip()
        except OSError:
            pass
        if first is not None and first != HEADER:
            old = self._path[:-4] + ".old.csv"
            try:
                os.remove(old)
            except OSError:
                pass
            try:
                os.rename(self._path, old)
            except OSError:
                pass
            first = None
        if first is None:
            with open(self._path, "w") as f:
                f.write(HEADER + "\n")
        self._ready = True
