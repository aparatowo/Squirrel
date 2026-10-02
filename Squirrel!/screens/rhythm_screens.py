# screens/rhythm_screens.py - Metronome and Breathing
#
# MetronomeScreen  LEFT/RIGHT interval (1, 2, 5, 30, 60, 120 s), UP/DOWN volume, ENTER start / stop, ESC leave.
#                  The metronome is a background service: it keeps ticking when you leave (a recording stops it).
#                  The last interval and volume are remembered (settings METRO_INTERVAL_S, METRO_VOLUME).
# BreathingScreen  LEFT/RIGHT choose the exercise, ENTER start / stop, ESC back.  A circle grows while you breathe in
#                  and shrinks while you breathe out.

import time
from gfx import Lcd
import intervals as iv
from appconfig import cfg
from screens.base_screen import BaseScreen

# name, seconds of: breathe in, hold, breathe out, hold
EXERCISES = (("Box 4-4-4-4", (4, 4, 4, 4)), ("Relax 4-7-8", (4, 7, 8, 0)), ("Calm 5-5", (5, 0, 5, 0)))
PHASES = ("Breathe in", "Hold", "Breathe out", "Hold")


def breath_phase(durations, elapsed_ms):
    """(phase number, seconds left in it, size of the circle 0..100) `elapsed_ms` into the exercise (it repeats)."""
    cycle = sum(durations) * 1000
    t = elapsed_ms % cycle
    for n, secs in enumerate(durations):
        length = secs * 1000
        if length == 0:
            continue
        if t < length:
            if n == 0:
                size = t * 100 // length
            elif n == 2:
                size = 100 - t * 100 // length
            else:
                size = 100 if n == 1 else 0
            return n, (length - t + 999) // 1000, size
        t -= length
    return 0, 0, 0


class MetronomeScreen(BaseScreen):
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self._drawn = None

    def on_enter(self, **kwargs):
        self._drawn = None

    def needs_refresh(self):
        m = self.app.metronome()
        return (m.running, m.beats) != self._drawn

    def handle_input(self, action):
        m = self.app.metronome()
        if action == 'ENTER':
            m.stop() if m.running else m.start()
        elif action in ('LEFT', 'RIGHT'):
            steps = iv.METRO_STEPS
            i = steps.index(cfg.get("METRO_INTERVAL_S")) if cfg.get("METRO_INTERVAL_S") in steps else 2
            cfg.set("METRO_INTERVAL_S", steps[max(0, min(len(steps) - 1, i + (1 if action == 'RIGHT' else -1)))])
        elif action in ('UP', 'DOWN'):
            cfg.set("METRO_VOLUME", max(0, min(100, cfg.get("METRO_VOLUME") + (10 if action == 'UP' else -10))))
        elif action in ('ESC', 'BACKSPACE'):
            self.app.set_screen("MENU", menu_name="FOCUS")

    def render(self, renderer):
        theme = renderer.theme
        m = self.app.metronome()
        self._drawn = (m.running, m.beats)
        renderer.clear()
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("Metronome", 5, 5)
        Lcd.setTextColor(theme["ACCENT"] if m.running else theme["WARNING"], theme["BG"])
        Lcd.drawString("TICKING" if m.running else "STOPPED", 170, 5)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.setTextSize(3)
        Lcd.drawString("%d s" % cfg.get("METRO_INTERVAL_S"), 70, 30)
        Lcd.setTextSize(1)
        Lcd.drawString("volume", 5, 80)
        Lcd.drawRect(60, 78, 102, 10, theme["FG"])
        Lcd.fillRect(61, 79, cfg.get("METRO_VOLUME"), 8, theme["ACCENT"])
        if m.running and m.beats % 2:
            Lcd.fillCircle(210, 40, 8, theme["WARNING"])                # a flash on every beat
        Lcd.drawString("<> interval  up/down volume", 5, 105)
        Lcd.setTextColor(theme["ACCENT"], theme["BG"])
        Lcd.drawString("[ENTER] %s  [ESC] Back" % ("Stop" if m.running else "Start"), 5, 119)


class BreathingScreen(BaseScreen):
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self.n = 0
        self.running = False
        self._t0 = 0
        self._full = True
        self._shown = None

    def on_enter(self, **kwargs):
        self.running, self._full, self._shown = False, True, None

    def _elapsed(self):
        return time.ticks_diff(time.ticks_ms(), self._t0)

    def _state(self):
        if not self.running:
            return None
        return breath_phase(EXERCISES[self.n][1], self._elapsed())

    def needs_refresh(self):
        s = self._state()
        return s is not None and (s[0], s[2] // 4) != self._shown

    def handle_input(self, action):
        self._full = True
        if action == 'ENTER':
            self.running = not self.running
            self._t0 = time.ticks_ms()
        elif action in ('LEFT', 'RIGHT') and not self.running:
            self.n = (self.n + (1 if action == 'RIGHT' else -1)) % len(EXERCISES)
        elif action == 'ESC':
            self.running = False
            self.app.set_screen("MENU", menu_name="FOCUS")

    def render(self, renderer):
        theme = renderer.theme
        s = self._state()
        if self._full:
            renderer.clear()
            Lcd.setTextSize(1)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString("Breathing", 5, 5)
            Lcd.drawString(EXERCISES[self.n][0], 120, 5)
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            Lcd.drawString("[ENTER] %s  <> exercise" % ("Stop" if self.running else "Start"), 5, 119)
            self._full = False
        Lcd.fillRect(0, 20, 240, 96, theme["BG"])
        if s is None:
            self._shown = None
            return
        self._shown = (s[0], s[2] // 4)
        Lcd.setTextColor(theme["WARNING"], theme["BG"])
        Lcd.drawString("%s  %d" % (PHASES[s[0]], s[1]), 5, 24)
        Lcd.fillCircle(120, 72, 8 + s[2] * 32 // 100, theme["ACCENT"])
