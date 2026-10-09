# battery.py - battery level, read every now and then in the background

import time


def _power_level():
    try:
        from M5 import Power
        return Power.getBatteryLevel()
    except Exception:
        return None


_PMIC_UNKNOWN, _PMIC_ADC = 0, 1      # M5 Power.getType(): no power chip that reports charging


def _power_charging():
    """True / False, or None when the device cannot tell.

    M5Unified answers "charge unknown" on boards without a charger chip it can read - the Cardputer ADV is one (its
    battery is only measured through the ADC) - and the MicroPython binding turns that into True.  Taken at face value
    the device would always be "charging", so on such boards the answer is None (unknown) instead."""
    try:
        from M5 import Power
        if Power.getType() in (_PMIC_UNKNOWN, _PMIC_ADC):
            return None
        return bool(Power.isCharging())
    except Exception:
        return None


class BatteryMonitor:
    """Service: polls the fuel gauge every `interval_ms`.  level() is None when it cannot be read."""

    def __init__(self, read=None, charging=None, interval_ms=30000):
        self._read = read or _power_level
        self._charging = charging or _power_charging
        self._interval = interval_ms
        self.level_pct = None
        self.charging = None             # True / False, or None: this device cannot tell
        self._next = 0
        self._poll()

    def level(self):
        return self.level_pct

    def tick(self):
        if time.ticks_diff(time.ticks_ms(), self._next) >= 0:
            self._poll()

    def _poll(self):
        self._next = time.ticks_add(time.ticks_ms(), self._interval)
        try:
            value = self._read()
        except Exception:
            value = None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or value > 100:
            self.level_pct = None
        else:
            self.level_pct = int(value)
        try:
            value = self._charging()
            self.charging = None if value is None else bool(value)
        except Exception:
            self.charging = None


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
        self._voltage = voltage or _power_millivolts
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
        mode = "lightsleep" if self._cfg.get("POWER_LIGHT_SLEEP") else ("slowcpu" if self._cfg.get("POWER_SAVE") else "full")
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


def _power_millivolts():
    try:
        from M5 import Power
        value = Power.getBatteryVoltage()
        return int(value) if isinstance(value, (int, float)) and value > 0 else None
    except Exception:
        return None

