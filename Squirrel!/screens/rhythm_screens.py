# screens/rhythm_screens.py - Metronome and Breathing
#
# MetronomeScreen  LEFT/RIGHT interval (1/8, 1/4, 1/2, 1, 2, 5, 30, 60, 120 s), UP/DOWN volume, S the sound (a beep /
#                  a click, METRO_SOUND), ENTER start / stop, ESC leave.  On a beat only the flashing dot is drawn again (at 1/8 s a full redraw would delay beats).
#                  The metronome is a background service: it keeps ticking when you leave (a recording stops it).
#                  The last interval and volume are remembered (settings METRO_INTERVAL_S, METRO_VOLUME).
# BreathingScreen  LEFT/RIGHT choose the exercise, ENTER start / stop, ESC back.  A circle grows while you breathe in
#                  and shrinks while you breathe out.  With LED_BREATHING on the LED follows it: green growing brighter
#                  while you breathe in (and held), blue fading while you breathe out, dark in the pause after it.
# On a touch screen (the watch) both use the whole panel: big numbers / a big circle, "-" / "+" and Start / Stop as
# buttons; a tap on the title (or a swipe right) goes back.

import time
from gfx import Lcd, SCREEN_W
import intervals as iv
from appconfig import cfg
from screens.base_screen import BaseScreen
from hw.led import led
from ui.touch import has_touch, TouchList, TouchPanel, Button, header_tapped, button_height, draw_centered
from i18n import _

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
        self._full = None            # (running, interval, volume) of the last full drawing
        self._beat_only = False      # the next drawing is for a beat alone: only the dot changes
        self._touch = has_touch()
        self._panel = TouchPanel() if self._touch else None
        self._list = TouchList() if self._touch else None
        self._dot = (210, 40, 8)     # where the beat flashes (the touch layout puts it elsewhere)

    @property
    def full_height(self):
        return self._touch

    def on_enter(self, **kwargs):
        self._drawn = None
        self._full = None
        self._beat_only = False

    def _state(self, m):
        return (m.running, cfg.get("METRO_INTERVAL_S"), cfg.get("METRO_VOLUME"), cfg.get("METRO_SOUND"))

    def needs_refresh(self):
        m = self.app.metronome()
        if (m.running, m.beats) == self._drawn:
            return False
        self._beat_only = self._state(m) == self._full    # any other drawing (a key, a closed notification ...) is full
        return True

    def _step_interval(self, delta):
        steps = iv.METRO_STEPS
        i = steps.index(cfg.get("METRO_INTERVAL_S")) if cfg.get("METRO_INTERVAL_S") in steps else steps.index(5)
        cfg.set("METRO_INTERVAL_S", steps[max(0, min(len(steps) - 1, i + delta))])

    def _step_volume(self, delta):
        cfg.set("METRO_VOLUME", max(0, min(100, cfg.get("METRO_VOLUME") + 10 * delta)))

    def handle_input(self, action):
        m = self.app.metronome()
        if self._touch:
            if action in ('ESC', 'LEFT') or (action in ('ENTER', 'OPT') and header_tapped(self.app.keypad)):
                self.app.set_screen("MENU", menu_name="FOCUS")
            else:
                self._panel.handle(action, self.app.keypad)
            self._full = None
            return
        if action == 'ENTER':
            m.stop() if m.running else m.start()
        elif action in ('LEFT', 'RIGHT'):
            self._step_interval(1 if action == 'RIGHT' else -1)
        elif action in ('UP', 'DOWN'):
            self._step_volume(1 if action == 'UP' else -1)
        elif action in ('s', 'S'):
            cfg.set("METRO_SOUND", "tone" if cfg.get("METRO_SOUND") == "click" else "click")
        elif action in ('ESC', 'BACKSPACE'):
            self.app.set_screen("MENU", menu_name="FOCUS")

    def render(self, renderer):
        theme = renderer.theme
        m = self.app.metronome()
        self._drawn = (m.running, m.beats)
        if self._beat_only:
            # only a beat: the dot flashes on every other beat (the rest of the screen is as it was)
            self._beat_only = False
            x, y, rad = self._dot
            Lcd.fillCircle(x, y, rad, theme["WARNING"] if m.running and m.beats % 2 else theme["BG"])
            return
        self._full = self._state(m)
        if self._touch:
            return self._render_touch(renderer, m)
        renderer.clear()
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(_("Metronome"), 5, 5)
        Lcd.setTextColor(theme["ACCENT"] if m.running else theme["WARNING"], theme["BG"])
        Lcd.drawString(_("TICKING") if m.running else _("STOPPED"), 170, 5)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.setTextSize(3)
        Lcd.drawString(iv.metro_label(cfg.get("METRO_INTERVAL_S")), 70, 30)
        Lcd.setTextSize(1)
        label = _("volume")
        Lcd.drawString(label, 5, 80)
        x = max(60, 17 + 6 * len(label))                                # the bar after the label, in any language
        Lcd.drawRect(x, 78, 102, 10, theme["FG"])
        Lcd.fillRect(x + 1, 79, cfg.get("METRO_VOLUME"), 8, theme["ACCENT"])
        Lcd.drawString(_("[S] sound: %s") % _(cfg.get("METRO_SOUND")), 5, 92)
        if m.running and m.beats % 2:
            Lcd.fillCircle(210, 40, 8, theme["WARNING"])                # a flash on every beat
        Lcd.drawString(_("<> interval  up/down volume"), 5, 105)
        Lcd.setTextColor(theme["ACCENT"], theme["BG"])
        Lcd.drawString(_("[ENTER] %s  [ESC] Back") % (_("Stop") if m.running else _("Start")), 5, 119)


    def _render_touch(self, renderer, m):
        theme = renderer.theme
        renderer.clear()
        w, h = Lcd.screen_size()
        top = TouchList.HEADER
        self._list.draw_header(theme, _("Metronome"))
        bw = button_height()
        p = self._panel
        p.clear()
        # the interval: - big label +
        y1 = top + 12
        p.add(Button(4, y1, bw, bw, "-"), lambda: self._step_interval(-1), repeat=True)
        p.add(Button(w - 4 - bw, y1, bw, bw, "+"), lambda: self._step_interval(1), repeat=True)
        draw_centered(iv.metro_label(cfg.get("METRO_INTERVAL_S")), y1 + (bw - 32) // 2, 4, theme["FG"], theme["BG"])
        # the volume: - bar +
        y2 = y1 + bw + 16
        p.add(Button(4, y2, bw, bw, "-"), lambda: self._step_volume(-1), repeat=True)
        p.add(Button(w - 4 - bw, y2, bw, bw, "+"), lambda: self._step_volume(1), repeat=True)
        bx, bwid = 4 + bw + 8, w - 2 * (4 + bw + 8)
        Lcd.drawRect(bx, y2 + bw // 2 - 8, bwid, 16, theme["FG"])
        Lcd.fillRect(bx + 1, y2 + bw // 2 - 7, (bwid - 2) * cfg.get("METRO_VOLUME") // 100, 14, theme["ACCENT"])
        draw_centered(_("volume"), y2 + bw // 2 + 12, 1, theme["FG"], theme["BG"])
        # start / stop, and the beat dot above it
        bh = button_height()
        p.add(Button(4, h - bh - 2, w - 8, bh, _("Stop") if m.running else _("Start"), "ACCENT"),
              lambda: m.stop() if m.running else m.start())
        self._dot = (w // 2, h - bh - 18, 8)
        p.draw(theme)
        if m.running and m.beats % 2:
            Lcd.fillCircle(self._dot[0], self._dot[1], self._dot[2], theme["WARNING"])


class BreathingScreen(BaseScreen):
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self.n = 0
        self.running = False
        self._t0 = 0
        self._full = True
        self._shown = None
        self._touch = has_touch()
        self._panel = TouchPanel() if self._touch else None
        self._list = TouchList() if self._touch else None

    @property
    def full_height(self):
        return self._touch

    def on_enter(self, **kwargs):
        self.running, self._full, self._shown = False, True, None

    def on_exit(self):
        self.running = False
        led.set_breath(None)

    def _led_state(self):
        """What the LED shows now (see led.set_breath): None when the light is off in the settings."""
        s = self._state()
        if s is None or not cfg.get("LED_BREATHING"):
            return None
        phase, _left, size = s
        if phase == 0:
            return ("green", size)               # breathing in: brighter and brighter
        if phase == 1:
            return ("green", 100)                # holding the breath
        if phase == 2:
            return ("blue", size)                # breathing out: fading
        return ("blue", 0)                       # the pause after breathing out: dark

    def _elapsed(self):
        return time.ticks_diff(time.ticks_ms(), self._t0)

    def _state(self):
        if not self.running:
            return None
        return breath_phase(EXERCISES[self.n][1], self._elapsed())

    def needs_refresh(self):
        s = self._state()
        return s is not None and (s[0], s[2] // 4) != self._shown

    def _toggle(self):
        self.running = not self.running
        self._t0 = time.ticks_ms()
        led.set_breath(self._led_state if self.running else None)

    def _choose(self, delta):
        if not self.running:
            self.n = (self.n + delta) % len(EXERCISES)

    def handle_input(self, action):
        self._full = True
        if self._touch:
            if action in ('ESC', 'LEFT') or (action in ('ENTER', 'OPT') and header_tapped(self.app.keypad)):
                self.running = False
                led.set_breath(None)
                self.app.set_screen("MENU", menu_name="FOCUS")
            else:
                self._panel.handle(action, self.app.keypad)
            return
        if action == 'ENTER':
            self._toggle()
        elif action in ('LEFT', 'RIGHT') and not self.running:
            self.n = (self.n + (1 if action == 'RIGHT' else -1)) % len(EXERCISES)
        elif action == 'ESC':
            self.running = False
            led.set_breath(None)
            self.app.set_screen("MENU", menu_name="FOCUS")

    def _render_touch(self, renderer, s):
        theme = renderer.theme
        w, h = Lcd.screen_size()
        top = TouchList.HEADER
        bh = button_height()
        rmax = (h - top - 2 * bh - 40) // 2
        cy = top + rmax
        if self._full:
            renderer.clear()
            self._list.draw_header(theme, _("Breathing"))
            p = self._panel
            p.clear()
            if not self.running:
                aw = (w - 12 * len(_(EXERCISES[self.n][0])) - 16) // 2         # the arrows take what the name leaves
                aw = max(22, min(bh, aw))
                p.add(Button(2, h - bh - 2 - bh - 6, aw, bh, "<"), lambda: self._choose(-1))
                p.add(Button(w - 2 - aw, h - bh - 2 - bh - 6, aw, bh, ">"), lambda: self._choose(1))
            p.add(Button(4, h - bh - 2, w - 8, bh, _("Stop") if self.running else _("Start"), "ACCENT"), self._toggle)
            p.draw(theme)
            draw_centered(_(EXERCISES[self.n][0]), h - bh - 2 - bh // 2 - 14, 2, theme["FG"], theme["BG"],
                          None if self.running else w - 2 * aw - 8)              # between the arrows
            self._full = False
        Lcd.fillRect(0, top, w, 2 * rmax + 20, theme["BG"])
        if s is None:
            self._shown = None
            return
        self._shown = (s[0], s[2] // 4)
        Lcd.fillCircle(w // 2, cy, 10 + s[2] * (rmax - 12) // 100, theme["ACCENT"])
        draw_centered("%s  %d" % (_(PHASES[s[0]]), s[1]), top + 2 * rmax + 4, 2, theme["WARNING"], theme["BG"])

    def render(self, renderer):
        theme = renderer.theme
        s = self._state()
        if self._touch:
            return self._render_touch(renderer, s)
        if self._full:
            renderer.clear()
            Lcd.setTextSize(1)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString(_("Breathing"), 5, 5)
            Lcd.drawString(_(EXERCISES[self.n][0]), 120, 5)
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            Lcd.drawString(_("[ENTER] %s  <> exercise") % (_("Stop") if self.running else _("Start")), 5, 119)
            self._full = False
        Lcd.fillRect(0, 20, SCREEN_W, 96, theme["BG"])
        if s is None:
            self._shown = None
            return
        self._shown = (s[0], s[2] // 4)
        Lcd.setTextColor(theme["WARNING"], theme["BG"])
        Lcd.drawString("%s  %d" % (_(PHASES[s[0]]), s[1]), 5, 24)
        Lcd.fillCircle(120, 72, 8 + s[2] * 32 // 100, theme["ACCENT"])
