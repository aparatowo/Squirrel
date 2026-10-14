# screens/silent_mode_screen.py - Settings -> Silent mode -> Sound / Buzzer / LED: the silent hours of one channel
#
# Opened with channel="sound", "buzzer" or "led" (see quiet_hours.py).  The values are QUIET_<CHANNEL>_FROM / _TO / _DAYS
# in config.txt; every change is saved at once.  From = To (e.g. 00:00 - 00:00) = no silent hours.
#
# form:   From / Until / Days - UP/DOWN, ENTER edits a row, DEL (FN + Backspace) puts its default back, ESC back
# time:   LEFT/RIGHT hour or minutes, UP/DOWN change it, ENTER accept, ESC cancel
# days:   LEFT/RIGHT choose a day, ENTER tick/untick it, ESC done (the same as in Routines)
# On a touch screen (the watch) everything is on one screen: From and Until with "-" / "+" (15 minutes a step; hold to
# keep changing), the seven days as buttons to tick, and whether it is silent now; every change is saved at once.
# A tap on the title (or a swipe right) goes back.

from gfx import Lcd
from appconfig import cfg, time_text, days_shown, day_short
from quiet_hours import keys, is_quiet
from screens.base_screen import BaseScreen
from ui.touch import has_touch, TouchList, TouchPanel, Button, header_tapped, button_height, draw_centered
from i18n import _

_TITLES = {"sound": "Silent mode: sound", "buzzer": "Silent mode: buzzer", "led": "Silent mode: LED"}
_BACK = ("MENU", {"menu_name": "SILENT"})


class SilentModeScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)
        self.channel = "sound"
        self.mode = "form"
        self.f = 0                 # highlighted row of the form
        self.sel = 0               # time: 0 = hour, 1 = minutes; days: the day under the cursor
        self.h = self.m = 0
        self.days = 0
        self._touch = has_touch()
        self._panel = TouchPanel() if self._touch else None
        self._list = TouchList() if self._touch else None

    @property
    def full_height(self):
        return self._touch

    def on_enter(self, channel="sound", **kwargs):
        self.channel = channel if channel in _TITLES else "sound"
        self.mode, self.f = "form", 0

    def _keys(self):
        return keys(self.channel)              # (from, to, days)

    def _form_rows(self):
        k_from, k_to, k_days = self._keys()
        start, end = cfg.get(k_from), cfg.get(k_to)
        rows = [_("From:  ") + time_text(start), _("Until: ") + time_text(end), _("Days:  ") + days_shown(cfg.get(k_days))]
        if start == end:
            rows.append(_("(From = Until: no silence)"))
        else:
            rows.append(_("Now: ") + (_("silent") if is_quiet(self.channel) else _("allowed")))
        return rows

    # ---------------------------------------------------------------- input

    def handle_input(self, action):
        if self._touch:
            if action in ('ESC', 'LEFT') or (action in ('ENTER', 'OPT') and header_tapped(self.app.keypad)):
                self.app.set_screen(_BACK[0], **_BACK[1])
            else:
                self._panel.handle(action, self.app.keypad)
            return
        getattr(self, "_in_" + self.mode)(action)

    def needs_refresh(self):
        return self._touch and self._panel.tick(self.app.keypad)

    def _step_time(self, which, delta):
        key = self._keys()[which]
        cfg.set(key, (cfg.get(key) + delta) % (24 * 60))

    def _toggle_day(self, n):
        key = self._keys()[2]
        cfg.set(key, cfg.get(key) ^ (1 << n))

    def _in_form(self, action):
        if action in ('UP', 'DOWN'):
            self.f = (self.f + (-1 if action == 'UP' else 1)) % 3
        elif action in ('ESC', 'LEFT'):
            self.app.set_screen(_BACK[0], **_BACK[1])
        elif action == 'DEL':
            cfg.reset(self._keys()[self.f])
        elif action in ('ENTER', 'RIGHT'):
            key = self._keys()[self.f]
            if self.f < 2:
                value = cfg.get(key)
                self.h, self.m, self.sel, self.mode = value // 60, value % 60, 0, "time"
            else:
                self.days, self.sel, self.mode = cfg.get(key), 0, "days"

    def _in_time(self, action):
        if action in ('LEFT', 'RIGHT'):
            self.sel = 1 - self.sel
        elif action in ('UP', 'DOWN'):
            d = 1 if action == 'UP' else -1
            if self.sel == 0:
                self.h = (self.h + d) % 24
            else:
                self.m = (self.m + d) % 60
        elif action == 'ENTER':
            cfg.set(self._keys()[self.f], self.h * 60 + self.m)
            self.mode = "form"
        elif action == 'ESC':
            self.mode = "form"

    def _in_days(self, action):
        if action == 'LEFT':
            self.sel = (self.sel - 1) % 7
        elif action == 'RIGHT':
            self.sel = (self.sel + 1) % 7
        elif action in ('ENTER', 'SPACE'):
            self.days ^= 1 << self.sel
        elif action == 'ESC':
            cfg.set(self._keys()[2], self.days)        # no day ticked = no silence at all
            self.mode = "form"

    # ---------------------------------------------------------------- drawing

    def _render_touch(self, renderer):
        theme = renderer.theme
        renderer.clear()
        w, h = Lcd.screen_size()
        top = TouchList.HEADER
        k_from, k_to, k_days = self._keys()
        self._list.draw_header(theme, _(_TITLES[self.channel].replace("Silent mode: ", "Silent: ")))
        p = self._panel
        p.clear()
        bw = button_height()
        y = top + 6
        for which, label in ((0, _("From")), (1, _("Until"))):
            p.add(Button(4, y, bw, bw, "-"), lambda which=which: self._step_time(which, -15), repeat=True)
            p.add(Button(w - 4 - bw, y, bw, bw, "+"), lambda which=which: self._step_time(which, 15), repeat=True)
            draw_centered(label, y + 2, 1, theme["FG"], theme["BG"])
            draw_centered(time_text(cfg.get(self._keys()[which])), y + 14, 3, theme["FG"], theme["BG"])
            y += bw + 6
        days = cfg.get(k_days)
        cw = (w - 8) // 7
        for n in range(7):
            on = days >> n & 1
            p.add(Button(4 + n * cw, y, cw - 2, bw, day_short(n), "ACCENT" if on else "FG"), lambda n=n: self._toggle_day(n))
        y += bw + 8
        if cfg.get(k_from) == cfg.get(k_to) or not days:
            status = _("no silence")
        else:
            status = _("now: ") + (_("silent") if is_quiet(self.channel) else _("allowed"))
        p.draw(theme, highlight=lambda b: b.label not in "+-" and b.color == "ACCENT")
        draw_centered(status, y, 2, theme["WARNING"], theme["BG"])

    def render(self, renderer):
        theme = renderer.theme
        if self._touch:
            return self._render_touch(renderer)
        if self.mode == "form":
            renderer.render_menu(_(_TITLES[self.channel]), self._form_rows(), self.f, 0, 5)
            return
        renderer.clear()
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString((_("Silent from"), _("Silent until"), _("Silent days"))[self.f], 5, 8)
        if self.mode == "time":
            for n, (text, x) in enumerate((("%02d" % self.h, 70), ("%02d" % self.m, 130))):
                Lcd.setTextColor(theme["WARNING"] if n == self.sel else theme["FG"], theme["BG"])
                Lcd.setTextSize(3)
                Lcd.drawString(text, x, 45)
            Lcd.setTextSize(1)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString(_("From = Until (00:00) = no silence"), 5, 95)
            Lcd.drawString(_("<> hour/min   up/down change   ENTER ok"), 5, 115)
        else:
            for n in range(7):
                on = self.days >> n & 1
                Lcd.setTextColor(theme["WARNING"] if n == self.sel else theme["FG"], theme["BG"])
                Lcd.drawString(("[%s]" if on else " %s ") % day_short(n), 20 + n * 28, 50)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString(_("A night counts for the day it starts"), 5, 80)
            Lcd.drawString(_("<> day   ENTER tick   ESC done"), 5, 115)
