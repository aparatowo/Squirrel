# led.py - the RGB LED built into the Cardputer ADV (one WS2812 on G21)
#
# Hardware: the port says whether there is one and where ([signal.led] in ports/<port>/port.toml); the board hands
# begin() the pin, the drivers to try (drivers/ws2812.py) and the limits below.  M5.Led is NOT used: here M5Unified is
# built with M5UNIFIED_RMT_VERSION 1, for which its LED bus has no code at all - every M5.Led call is silently ignored,
# while getCount() still says 1.  It stays only as a last resort (the board's `fallback`) when both drivers fail.
#
# Power: the LED gets its supply through the LCD back-light's switched (PWM) supply.  Below a back-light of about 200 it
# resets after a flash; at 0 it is dead (measured - this, not the data, was why it "flashed once and went dark").  While
# it shows something it asks for a minimum back-light (backlight_floor(), applied by screen_dimmer.py).
#
# Driver: one esp32.RMT channel set up ONCE, its line idle low.  machine.bitstream (the first try) installs an RMT
# driver for every frame, uninstalls it and gives the pin back to plain GPIO afterwards - the pin was created without a
# level, so between frames the line could sit anywhere, and the LED misread frames (flicker, colours not appearing,
# "off" missed).  machine.bitstream stays as a fallback, with the pin explicitly low.
# Sending: a change is sent at once and repeated as SEND_MODES[SEND_MODE] says (a lost frame is made good); refreshing a
# steady colour often only gave every glitch a new chance to show.  Frames sent right after the screen was redrawn were
# seen to be lost in the app, hence the modes with later repeats - compared on the device with the LED tests (key R).
#
# What it shows, most important first:
#   1. a signal - a mode (MODES) in a colour, started by signal(feature) or play(mode, colour);
#   2. Breathing - while the exercise runs and LED_BREATHING is on: green growing brighter while you breathe in,
#      blue fading while you breathe out (set_breath());
#   3. charging - while the battery charges and LED_CHARGING is on: a slow blink in the colour of the battery level,
#      the same colours as the status bars (blue, green, yellow, red).  Only when the device REPORTS charging: the
#      Cardputer ADV cannot (see battery.py), so there the light stays off rather than blinking all the time;
#   otherwise it is dark.
#
# Which features may light it, in which mode and colour: the settings of the group "LED" (all "off" by default),
# read from the settings in memory (appconfig.cfg).  The quiet hours of the LED (QUIET_LED_*, Settings -> Silent mode) darken the signals and the charging light; signal() is wrapped in
# quiet_hours.quiet_guard("led"), so force=True lights it anyway.  Breathing is started by hand and always lights.

import time
from boot_log import log
from appconfig import cfg
from quiet_hours import quiet_guard, is_quiet

# Modes: segments of (ms, level at the start %, level at the end %) - a level changes evenly within a segment
MODES = {
    "flash":  ((150, 100, 100),),
    "double": ((120, 100, 100), (120, 0, 0), (120, 100, 100)),
    "triple": ((90, 100, 100), (90, 0, 0), (90, 100, 100), (90, 0, 0), (90, 100, 100)),
    "long":   ((800, 100, 100),),
    "pulse":  ((500, 0, 100), (500, 100, 0)),
    "alarm":  ((150, 100, 100), (100, 0, 0), (150, 100, 100), (100, 0, 0), (150, 100, 100), (100, 0, 0),
               (150, 100, 100)),
    "sos":    ((100, 100, 100), (100, 0, 0), (100, 100, 100), (100, 0, 0), (100, 100, 100), (250, 0, 0),
               (300, 100, 100), (100, 0, 0), (300, 100, 100), (100, 0, 0), (300, 100, 100), (250, 0, 0),
               (100, 100, 100), (100, 0, 0), (100, 100, 100), (100, 0, 0), (100, 100, 100)),
}
MODE_NAMES = ("flash", "double", "triple", "long", "pulse", "alarm", "sos")

# Features that may light the LED: LED_<NAME> is the mode ("off" = not at all), LED_<NAME>_COLOR the colour
FEATURES = ("LED_NOTIFY", "LED_INTERVALS", "LED_METRONOME", "LED_CUCKOO")

# The colour names of nuts.PALETTE as 0xRRGGBB for the LED (yellow and orange are shifted to red: a WS2812 shows
# full red + green as a greenish yellow)
RGB = {
    "black": 0x000000, "white": 0xFFFFFF, "red": 0xFF0000, "green": 0x00FF00, "blue": 0x0000FF,
    "yellow": 0xFFA000, "cyan": 0x00FFFF, "magenta": 0xFF00FF, "gray": 0x808080, "darkgray": 0x303030,
    "lightgray": 0xC0C0C0, "orange": 0xFF3000, "lightgreen": 0x60FF30,
}

_CHARGE_BLINK_MS = 1000         # charging: 1 s lit, 1 s dark
# How a change is sent (the LED tests switch between these with R, to compare them on the device):
#   (name, gaps in ms before each repeat of the same frame, refresh period in ms while lit - 0 = none)
SEND_MODES = (
    ("1 frame", (), 0),
    ("+2 @20ms", (20, 20), 0),
    ("+0.25s +1s", (250, 750), 0),            # the repeats well away from the screen being redrawn
    ("refresh 2s", (250, 750), 2000),         # ... and again every 2 s while lit: a corrupted frame lasts <= 2 s
)
SEND_MODE = 1                   # the one in use (an index into SEND_MODES)
_LEAD_IN_MS = 80                # a signal starting from dark waits this long: the back-light is raised first and the
                                # LED, which gets its power through it, needs a moment before it takes data
_QUIET_CHECK_MS = 5000          # how often the charging light asks whether the quiet hours have begun




_max_sum = 765                  # the most R + G + B the LED may get (the port's max_sum, set by Led.begin())


def _fit(r, g, b):
    """r, g, b dimmed in proportion so that r + g + b stays within the port's max_sum (more current than the LED's
    supply can give makes it reset and go dark); returned as 0xRRGGBB."""
    total = r + g + b
    limit = _max_sum
    if total > limit:
        r, g, b = r * limit // total, g * limit // total, b * limit // total
    return r << 16 | g << 8 | b


class Led:
    def __init__(self):
        self._hw = None             # a drivers.ws2812 object, or (last resort) M5.Led
        self._np = False
        self._battery = None        # BatteryMonitor (level_pct, charging)
        self._pattern = None        # (segments, 0xRRGGBB, start ms)
        self._breath = None         # function -> (colour name, level %) or None
        self._shown = None          # the 0xRRGGBB written last
        self._sent_at = 0           # when a frame was last sent
        self._gaps = ()             # the repeats still to come for the last change (ms before each)
        self._test = None           # function -> raw 0xRRGGBB: the LED tests (Experimental), above everything else
        self.send_mode = SEND_MODE  # index into SEND_MODES; the LED tests switch it
        self.frames = 0             # frames sent since start-up (shown by the LED tests)
        self._floor = 0             # the port's min_backlight (set by begin())
        self.min_backlight = 0      # the floor asked for; the LED tests switch it
        self._pin = None
        self._drivers = ()          # the driver classes to try, in order (begin(), use_driver())
        self._quiet = False         # the LED's quiet hours, as of the last check
        self._quiet_at = 0
        self.problem = ""

    @property
    def available(self):
        return self._hw is not None

    def backlight_floor(self):
        """The lowest LCD back-light the LED needs right now: the port's min_backlight while it has something to show
        (lit, a signal or a test running, the breathing light on, a change still being confirmed), else 0.  With every
        LED feature off it is always 0: the back-light then does exactly what the screen settings say."""
        if self._hw is None:
            return 0
        if self._shown or self._pattern is not None or self._test is not None or self._gaps:
            return self.min_backlight
        if self._breath is not None:
            try:
                if self._breath() is not None:       # None = the breathing light is switched off: no floor for it
                    return self.min_backlight
            except Exception:
                pass
        return 0

    @property
    def busy(self):
        """True while the main loop must keep running quickly: a signal plays, a test runs, or a change is still being
        confirmed."""
        return self._pattern is not None or self._test is not None or bool(self._gaps)

    def status(self):
        """One short line for the screen: "ready" or why it cannot be used."""
        if self._hw is not None:
            return ("ready, G%d %s" % (self._pin, self._hw.name)) if self._np else "M5.Led (may not work)"
        return self.problem or "not started"

    def begin(self, battery=None, pin=None, drivers=(), fallback=None, min_backlight=0, max_sum=765):
        """Find the LED and switch it off.  Call once, after the board's begin().

        pin None = the device has no LED.  drivers: classes taking the pin number, tried in order (drivers/ws2812.py);
        fallback() -> an M5.Led-like object, the last resort; min_backlight / max_sum: see [signal.led] in port.toml."""
        global _max_sum
        self._battery = battery
        if pin is None:
            self.problem = "No LED (port.toml)"
            return False
        self._pin = pin
        self._drivers = drivers
        self._floor = self.min_backlight = min_backlight
        _max_sum = max_sum
        for driver in drivers:
            try:
                self._hw = driver(pin)
                self._np = True
                break
            except Exception as e:
                log(f"[LED] {driver.name} on G{pin} unavailable: {e}")
        if self._hw is None and fallback is not None:
            try:
                hw = fallback()
                if hw.getCount() > 0:
                    hw.setBrightness(255)            # the brightness is applied here, to each colour
                    self._hw = hw
            except Exception as e:
                log(f"[LED] M5.Led unavailable: {e}")
        if self._hw is None:
            self.problem = "LED error"
            return False
        self._shown = None                           # force the first write: the LED may hold a colour from before
        self._write(0)
        log(f"[LED] ready ({'WS2812 on G%d via %s' % (pin, self._hw.name) if self._np else 'M5.Led - may do nothing, see led.py'})")
        return True

    # ---------------------------------------------------------------- what to show

    @quiet_guard("led")
    def signal(self, feature):
        """Light the mode and colour the settings give `feature` (see FEATURES).

        Returns True when a signal was started.  Skipped during the LED's quiet hours, unless force=True."""
        if self._hw is None or feature not in FEATURES:
            return False
        mode = cfg.get(feature)
        if mode == "off":
            return False
        return self.play(mode, cfg.get(feature + "_COLOR"))

    def play(self, mode, color="green"):
        """Light `mode` in `color` (a colour name) whatever the settings say (the LED test, Settings -> Experimental)."""
        if self._hw is None:
            return False
        segments = MODES.get(mode)
        if segments is None:
            log(f"[LED] unknown mode {mode!r}")
            return False
        start = time.ticks_ms()
        if not self.backlight_floor():               # dark until now: the LED may have no power yet
            start = time.ticks_add(start, _LEAD_IN_MS)
        self._pattern = (segments, RGB.get(color, 0xFFFFFF), start)
        self.tick()
        return True

    def set_breath(self, provider):
        """provider() -> (colour name, level 0..100) while the exercise shows a light, or None (then the charging
        light may show).  Asked on every tick; set_breath(None) ends it."""
        self._breath = provider
        self.tick()

    def use_driver(self, name):
        """Switch to the driver called `name` ("RMT" / "bitstream") - for the LED tests.  Returns the name in use."""
        if not self._np or self._hw.name == name:
            return self._hw.name if self._hw is not None else ""
        for driver in self._drivers:
            if driver.name == name:
                try:
                    new = driver(self._pin)
                except Exception as e:
                    log(f"[LED] cannot switch to {name}: {e}")
                    break
                self._hw.release()
                self._hw = new
                self._shown = None                   # send the current colour through the new driver
        return self._hw.name

    def set_test(self, provider):
        """provider() -> a raw 0xRRGGBB (no brightness setting applied), asked on every tick, above everything else;
        set_test(None) ends it.  For the LED tests in Settings -> Experimental."""
        self._test = provider
        if provider is None:
            self.send_mode = SEND_MODE
            self.min_backlight = self._floor
        self.tick()

    def demo(self, feature):
        """Show the mode and colour just chosen for `feature` (Personalize), or a flash after a brightness change.
        Shown whatever the quiet hours say: the user has just asked for it."""
        if feature in FEATURES:
            mode = cfg.get(feature)
            return self.play("flash" if mode == "off" else mode, cfg.get(feature + "_COLOR"))
        return self.play("long", "white")

    def off(self):
        """Dark now: the signal and the breathing light are forgotten (the charging light comes back by itself)."""
        self._pattern = None
        self._breath = None
        self._write(0)

    # ---------------------------------------------------------------- service

    def tick(self):
        if self._hw is None:
            return
        now = time.ticks_ms()
        if self._test is not None:
            try:
                self._write(self._test())
            except Exception as e:
                log(f"[LED] test: {e}")
                self._test = None
            return
        if self._pattern is not None:
            color, level = self._pattern_level(now)
            if self._pattern is not None:              # still playing (else: fall through to what is under it)
                self._write(self._scale(color, level))
                return
        state = None
        if self._breath is not None:
            try:
                state = self._breath()
            except Exception as e:
                log(f"[LED] breathing: {e}")
                self._breath = None
        if state is not None:                          # the exercise runs: its light, dark pauses included
            color, level = RGB.get(state[0], 0), state[1]
        else:
            color, level = self._charging_level(now)
        self._write(self._scale(color, level))

    def _pattern_level(self, now):
        segments, color, start = self._pattern
        t = time.ticks_diff(now, start)
        if t < 0:
            return 0, 0                              # the lead-in: dark while the back-light comes up
        for ms, a, b in segments:
            if t < ms:
                return color, a + (b - a) * t // ms
            t -= ms
        self._pattern = None                         # played to the end
        return 0, 0

    def _charging_level(self, now):
        battery = self._battery
        if battery is None or battery.charging is not True or not cfg.get("LED_CHARGING"):    # only a real "charging"
            return 0, 0
        if time.ticks_diff(now, self._quiet_at) >= 0:
            self._quiet_at = time.ticks_add(now, _QUIET_CHECK_MS)
            self._quiet = is_quiet("led")
        if self._quiet or (now // _CHARGE_BLINK_MS) % 2:
            return 0, 0
        level = battery.level_pct
        if level is None:
            return RGB["white"], 100
        from bars import battery_color
        name = battery_color(level, cfg.get("BATTERY_BLUE_PCT"), cfg.get("BATTERY_GREEN_PCT"), cfg.get("BATTERY_YELLOW_PCT"))
        return RGB[name], 100

    @staticmethod
    def _scale(color, level):
        """0xRRGGBB at `level` percent and LED_BRIGHTNESS percent, within the LED's power budget (the port's max_sum).
        The level is squared: the eye sees a fade as even."""
        if not color or level <= 0:
            return 0
        factor = level * level * cfg.get("LED_BRIGHTNESS")          # up to 100 * 100 * 100
        r = (color >> 16 & 0xFF) * factor // 1000000
        g = (color >> 8 & 0xFF) * factor // 1000000
        b = (color & 0xFF) * factor // 1000000
        return _fit(r, g, b)

    def _write(self, rgb):
        """Show `rgb`: at once when it changes, then again and again (see the top of this file)."""
        if self._hw is None:
            return
        now = time.ticks_ms()
        _name, gaps, refresh = SEND_MODES[self.send_mode]
        if rgb != self._shown:
            self._shown = rgb
            self._gaps = gaps
        elif self._gaps and time.ticks_diff(now, self._sent_at) >= self._gaps[0]:
            self._gaps = self._gaps[1:]              # the same frame once more, in case the last one was lost
        elif rgb and refresh and not self._gaps and time.ticks_diff(now, self._sent_at) >= refresh:
            pass                                     # lit: refreshed now and then
        else:
            return                                   # nothing changed: nothing is sent
        self._sent_at = now
        self._send(rgb)

    def _send(self, rgb):
        self.frames += 1
        try:
            if self._np:
                self._hw.show(rgb)
            else:
                self._hw.setAllColor(rgb)
                self._hw.display()
        except Exception as e:
            log(f"[LED] {e}")


# The one shared instance.  SquirrelApp calls begin() and ticks it as a service.
led = Led()


def signal(feature, force=False):
    """Shortcut: led.signal(feature); force=True lights it during the quiet hours too."""
    if not led.available:
        return False
    return led.signal(feature, force=force)
