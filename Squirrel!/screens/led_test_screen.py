# screens/led_test_screen.py - Settings -> Experimental -> LED test: four tests of the LED, one at a time
#
# Opened with test=
#   "colors"  steady colours, one after another;
#   "blink"   on / off at different intervals;
#   "steps"   brightness in jumps: green, then white (raw values: neither the LED brightness setting nor the power
#             budget LED_MAX_SUM is applied - the test is there to find where the LED stops coping);
#   "fade"    brightness rising and falling smoothly, at different speeds (within the power budget LED_MAX_SUM, like
#             Breathing).
# Each test is a list of numbered steps that follow each other by themselves (and start again after the last), so it
# can be said exactly which step misbehaved.  The LED is driven through hw.led, the same code the rest of the program
# uses (led.set_test() puts the test above everything else the LED might show).
#
#   LEFT / RIGHT  previous / next step
#   R             how a change is sent: led.SEND_MODES in turn (one frame, repeats 20 ms apart, repeats after 0.25 s
#                 and 1 s, the same plus a refresh every 2 s)
#   D             driver: RMT (one channel, set up once) / bitstream (machine.bitstream, the earlier way)
#   S             speaker on / off (a running speaker amplifier may disturb the LED's supply)
#   B             the back-light floor while the LED shows something: 220 / 255 (nuts.LED_MIN_BACKLIGHT; 255 = no PWM at all)
# The screen also shows how many frames have been sent: flicker while that number stands still does not come from data.
#   ESC           back (the LED goes dark, the driver goes back to RMT)

import time
from gfx import Lcd
from hw.led import led, RGB, SEND_MODES, _fit
from screens.base_screen import BaseScreen

_GREEN = 0x00FF00
# (step label, what the step needs, how long it lasts in ms)
_TESTS = {
    "colors": ("Steady colours", [(name.upper(), RGB[name], 4000) for name in
                                  ("red", "green", "blue", "yellow", "cyan", "magenta", "orange", "white")]),
    "blink": ("Blink intervals", [("%d ms on / off" % ms, ms, 6000) for ms in (1000, 500, 250, 100, 50)]),
    "steps": ("Brightness steps", [("green %d / 255" % v, v << 8, 3000) for v in (255, 128, 64, 32, 16, 8, 4, 2, 1, 0)]
                                  + [("white %d" % v, v * 0x010101, 3000) for v in (255, 192, 128, 96, 76, 64, 32)]),
    "fade": ("Smooth fade", [("%d s up and down" % (ms // 1000), ms, 8000) for ms in (4000, 2000, 1000)]),
}


class LedTestScreen(BaseScreen):
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self.test = "colors"
        self.step = 0
        self._t0 = 0                 # when the current step began
        self._drawn = None
        self._frames_drawn = None    # the frame counter on screen, and when it was drawn
        self._frames_at = 0
        self._frames_only = False    # the next drawing is for the counter alone

    def on_enter(self, test="colors", **kwargs):
        self.test = test if test in _TESTS else "colors"
        self.step = 0
        self._t0 = time.ticks_ms()
        self._drawn = None
        led.set_test(self._rgb)

    def on_exit(self):
        led.set_test(None)
        led.use_driver("RMT")

    def _steps(self):
        return _TESTS[self.test][1]

    def _advance(self, now):
        """Go on to the next step when the current one has lasted long enough."""
        steps = self._steps()
        while time.ticks_diff(now, self._t0) >= steps[self.step][2]:
            self._t0 = time.ticks_add(self._t0, steps[self.step][2])
            self.step = (self.step + 1) % len(steps)

    def _rgb(self):
        """What the LED shows now (raw 0xRRGGBB) - asked by the LED driver on every tick."""
        now = time.ticks_ms()
        self._advance(now)
        _label, value, _ms = self._steps()[self.step]
        t = time.ticks_diff(now, self._t0)
        if self.test == "colors":
            return led._scale(value, 100)                       # at the LED brightness setting, like the program
        if self.test == "blink":
            return led._scale(_GREEN, 100) if (t // value) % 2 == 0 else 0
        if self.test == "steps":
            return value                                        # raw: no brightness setting, no power budget
        phase = t % value                                       # fade: a triangle 0 -> 255 -> 0 over `value` ms
        half = value // 2
        level = phase * 255 // half if phase < half else (value - phase) * 255 // half
        return _fit(0, min(255, level), 0)

    def handle_input(self, action):
        if action in ('ESC', 'BACKSPACE'):
            self.on_exit()
            self.app.set_screen("MENU", menu_name="LED_TEST")
        elif action in ('LEFT', 'RIGHT'):
            n = len(self._steps())
            self.step = (self.step + (1 if action == 'RIGHT' else -1)) % n
            self._t0 = time.ticks_ms()
        elif action in ('r', 'R'):
            led.send_mode = (led.send_mode + 1) % len(SEND_MODES)
        elif action in ('d', 'D'):
            led.use_driver("bitstream" if led.status().endswith("RMT") else "RMT")
        elif action in ('b', 'B'):
            led.min_backlight = 220 if led.min_backlight == 255 else 255
        elif action in ('s', 'S'):
            audio = getattr(self.app, "audio", None)
            if audio is not None:
                audio.set_speaker(not audio.speaker_on)

    def needs_refresh(self):
        self._advance(time.ticks_ms())
        if self._state() != self._drawn:
            self._frames_only = False
            return True
        # the frame counter alone: at most 4 times a second, drawn on its own (see render)
        self._frames_only = led.frames != self._frames_drawn and time.ticks_diff(time.ticks_ms(), self._frames_at) >= 250
        return self._frames_only

    def _state(self):
        audio = getattr(self.app, "audio", None)
        return (self.step, led.send_mode, led.status(), bool(audio is not None and audio.speaker_on), led.min_backlight)

    def _draw_frames(self, theme):
        self._frames_drawn = led.frames
        self._frames_at = time.ticks_ms()
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.fillRect(150, 106, 90, 12, theme["BG"])
        Lcd.drawString("frames %d" % led.frames, 150, 108)

    def render(self, renderer):
        theme = renderer.theme
        title, steps = _TESTS[self.test]
        label = steps[self.step][0]
        state = self._state()
        if self._frames_only:                       # only the counter changed (any other drawing is a full one)
            self._frames_only = False
            self._draw_frames(theme)
            return
        self._drawn = state
        renderer.clear()
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("# LED test: " + title, 5, 5)
        Lcd.drawString("step %d of %d" % (self.step + 1, len(steps)), 5, 24)
        Lcd.setTextSize(3)
        Lcd.setTextColor(theme["WARNING"], theme["BG"])
        Lcd.drawString(str(self.step + 1), 200, 20)
        Lcd.setTextSize(2)
        Lcd.drawString(label[:19], 5, 52)
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["ACCENT"], theme["BG"])
        Lcd.drawString("R sending: %d/%d %s" % (led.send_mode + 1, len(SEND_MODES), SEND_MODES[led.send_mode][0]), 5, 84)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("D driver:  " + led.status().rsplit(" ", 1)[-1], 5, 96)
        Lcd.drawString("B light %d" % led.min_backlight, 150, 96)
        Lcd.setTextColor(theme["WARNING"] if state[3] else theme["FG"], theme["BG"])
        Lcd.drawString("S speaker: " + ("ON" if state[3] else "off"), 5, 108)
        self._draw_frames(theme)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("<> step  R D S B  ESC back", 5, 122)
