# power.py - memory and energy
#
# MEMORY.  collect() runs the garbage collector; the app calls it right before a rarely used screen is imported
# (compiling a module needs a large contiguous block, and the heap is fragmented by then) and when a screen is
# given back.  PowerManager also collects every 30 s while the device is otherwise idle, and sets a GC threshold so
# that the collector runs early and often in small steps instead of rarely and late.
#
# ENERGY (everything here is off by default or harmless; see POWER_SAVE / POWER_LIGHT_SLEEP):
#   * imu_off(): the BMI270 motion sensor is not used - its accelerometer, gyroscope and temperature are switched off.
#   * while the screen is dimmed and nothing is going on: the CPU runs at 80 MHz instead of 240, and the main loop
#     pauses 50 ms instead of 20.
#   * POWER_LIGHT_SLEEP (experimental): while the screen is dimmed and nothing is going on, the chip light-sleeps
#     for ~0.8 s at a time; G0 and the keyboard controller's INT line (GPIO 11) wake it at once.  The USB console
#     (Thonny) disconnects in light sleep, hence it is off by default.
# Wi-Fi and Bluetooth are already powered down by radio.py unless a network task runs.

import gc
import time
from boot_log import log

_BMI270_ADDRS = (0x69, 0x68)
_BMI270_PWR_CTRL = 0x7D         # bits: aux, gyr, acc, temp enable - 0 = all off
_FAST_HZ_DEFAULT = 240_000_000
_SLOW_HZ = 80_000_000
_WAKE_PINS = (0, 11)            # G0, keyboard controller INT
_GC_EVERY_MS = 30_000
LOW_HEAP = 30_000             # free bytes after a collection below which a line is written to the log


def collect():
    """Collect garbage; returns the free bytes afterwards (0 if the platform cannot say)."""
    gc.collect()
    try:
        return gc.mem_free()
    except Exception:
        return 0


def imu_off(i2c):
    """Switch the BMI270's sensors off.  Returns the address that answered, or None."""
    if i2c is None:
        return None
    for addr in _BMI270_ADDRS:
        try:
            i2c.writeto_mem(addr, _BMI270_PWR_CTRL, b"\x00")
            return addr
        except Exception:
            continue
    return None


class PowerManager:
    def __init__(self, cfg, dimmer, busy, machine=None, keypad=None, now_ms=None):
        self._cfg = cfg
        self._dimmer = dimmer
        self._busy = busy                 # function: True while something needs the CPU at full speed
        self._mp = machine
        self._keypad = keypad
        self._now = now_ms or time.ticks_ms
        self._fast = _FAST_HZ_DEFAULT
        self.slow = False
        self._last_gc = self._now()
        self._last_tick = -1000
        self._armed = False
        self._sleep_broken = False
        self.sleeps = 0
        self.clock_fixes = 0

    def start(self, i2c=None):
        """Once, at start-up."""
        free = collect()
        try:
            gc.threshold(free // 4 + gc.mem_alloc())      # collect after every quarter of the free heap that is used
        except Exception:
            pass
        if self._mp is not None:
            try:
                self._fast = self._mp.freq()
            except Exception:
                pass
        addr = imu_off(i2c)
        log(f"[POWER] start-up: free heap {free} bytes, CPU {self._fast // 1000000} MHz, "
            f"IMU {'off (0x%02x)' % addr if addr else 'not reached'}")

    # ---- the main loop asks ----
    def dimmed_and_quiet(self):
        return bool(self._cfg.get("POWER_SAVE") and self._dimmer.dimmed and not self._busy())

    def pause_ms(self):
        return 50 if self.dimmed_and_quiet() else 20

    def tick(self):
        now = self._now()
        if time.ticks_diff(now, self._last_tick) < 1000:
            return
        self._last_tick = now
        slow = self.dimmed_and_quiet()
        if slow != self.slow and self._mp is not None:
            try:
                self._mp.freq(_SLOW_HZ if slow else self._fast)
                self.slow = slow
                log(f"[POWER] CPU {(_SLOW_HZ if slow else self._fast) // 1000000} MHz")
            except Exception as e:
                log(f"[POWER] cannot change the CPU frequency: {e}")
                self.slow = slow
        if time.ticks_diff(now, self._last_gc) >= _GC_EVERY_MS and not self._busy():
            self._last_gc = now
            free = collect()
            if free and free < LOW_HEAP:
                log(f"[MEM] low: only {free} bytes free after a collection")

    def _repair_clock(self, wall_ns, ticks_before):
        """After a light sleep the wall clock must show: the time before + the time the TICK counter measured.

        Measured on the device: ticks_ms() runs through a light sleep (5006 ms for a 5000 ms sleep), time.time() did NOT
        (it came back 3 s EARLIER).  Everything that is scheduled by the time of day (cuckoo, routines, dates) reads the wall
        clock, so it is set right from the reliable counter.  Never raises: a clock that cannot be corrected is only logged."""
        try:
            expected = wall_ns + time.ticks_diff(self._now(), ticks_before) * 1000000
            error_ms = (time.time_ns() - expected) // 1000000
            if abs(error_ms) < 100:
                return
            seconds, rest = divmod(expected, 1000000000)
            t = time.localtime(seconds)
            if t[0] < 2024:                      # the clock was never set: nothing to keep right
                return
            self._mp.RTC().datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], rest // 1000))
            self.clock_fixes += 1
            if self.clock_fixes <= 3 or self.clock_fixes % 100 == 0:
                log(f"[POWER] wall clock was {error_ms} ms off after a light sleep: corrected (#{self.clock_fixes})")
        except Exception as e:
            if self.clock_fixes == 0:
                self.clock_fixes = -1            # say it once
                log(f"[POWER] cannot correct the clock after a light sleep: {type(e).__name__}: {e}")

    def maybe_sleep(self):
        """Light-sleep for a moment if allowed.  Returns True if it did."""
        if (self._mp is None or self._sleep_broken or not self._cfg.get("POWER_LIGHT_SLEEP")
                or not self._dimmer.dimmed or self._busy()):
            return False
        try:
            if not self._armed:
                for number in _WAKE_PINS:
                    pin = self._mp.Pin(number, self._mp.Pin.IN, self._mp.Pin.PULL_UP)
                    pin.irq(trigger=self._mp.Pin.IRQ_LOW_LEVEL, wake=self._mp.SLEEP)
                self._armed = True
            if self._keypad is not None:
                self._keypad.acknowledge()
            wall_before, ticks_before = time.time_ns(), self._now()
            self._mp.lightsleep(800)
            self.sleeps += 1
            self._repair_clock(wall_before, ticks_before)
            return True
        except Exception as e:
            self._sleep_broken = True
            log(f"[POWER] light sleep unavailable: {type(e).__name__}: {e}")
            return False
