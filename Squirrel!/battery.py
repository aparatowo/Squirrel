# battery.py - battery level, read every now and then in the background

import time


def _power_level():
    try:
        from M5 import Power
        return Power.getBatteryLevel()
    except Exception:
        return None


def _power_charging():
    try:
        from M5 import Power
        return bool(Power.isCharging())
    except Exception:
        return False


class BatteryMonitor:
    """Service: polls the fuel gauge every `interval_ms`.  level() is None when it cannot be read."""

    def __init__(self, read=None, charging=None, interval_ms=30000):
        self._read = read or _power_level
        self._charging = charging or _power_charging
        self._interval = interval_ms
        self.level_pct = None
        self.charging = False
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
            self.charging = bool(self._charging())
        except Exception:
            self.charging = False


class BatteryLogger:
    """Service, off unless BATTERY_LOG is on: one line every 10 minutes in a CSV on the SD card.

    Measuring beats guessing: leave the device in one power mode for a day, then compare the %/hour between the modes.
    Columns: time (local, or uptime if the clock is not set), level %, charging 0/1, mV, screen, power mode."""

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

    def tick(self):
        if not self._cfg.get("BATTERY_LOG"):
            return
        now = self._now()
        if time.ticks_diff(now, self._next) < 0:
            return
        self._next = time.ticks_add(now, self._interval)
        t = self._localtime()
        stamp = "%04d-%02d-%02d %02d:%02d" % (t[0], t[1], t[2], t[3], t[4]) if t[0] >= 2024 else "up%ds" % (now // 1000)
        mode = "lightsleep" if self._cfg.get("POWER_LIGHT_SLEEP") else ("slowcpu" if self._cfg.get("POWER_SAVE") else "full")
        level = self._monitor.level()
        line = "%s,%s,%d,%s,%s,%s\n" % (stamp, "" if level is None else level, 1 if self._monitor.charging else 0,
                                        self._voltage() or "", "off" if self._dimmer.dimmed else "on", mode)
        try:
            import os
            folder = self._path.rpartition("/")[0]
            try:
                os.mkdir(folder)
            except OSError:
                pass
            new = False
            try:
                os.stat(self._path)
            except OSError:
                new = True
            with open(self._path, "a") as f:
                if new:
                    f.write("time,level_pct,charging,mv,screen,mode\n")
                f.write(line)
        except OSError:
            pass


def _power_millivolts():
    try:
        from M5 import Power
        value = Power.getBatteryVoltage()
        return int(value) if isinstance(value, (int, float)) and value > 0 else None
    except Exception:
        return None

