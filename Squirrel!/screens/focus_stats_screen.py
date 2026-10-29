# screens/focus_stats_screen.py - today's focus time and the last 7 days
#
# ENTER  - start / pause the focus timer
# -      - take FOCUS_UNDO_MIN (15) minutes back from today: a distraction that was counted as focus
# DEL    - zero today's focus time (DEL again within 3 s to confirm)
# LEFT / RIGHT - whose statistics: this device, each synced device (what it reported at the last Bluetooth sync,
#          ble/peers.py), or all of them together - only when there are synced devices
# ESC    - back to the main menu
# Redraws once a second while the timer runs (the seconds counter is live): on the Cardputer only today's time and
# today's bar, the rest of the screen stays (a whole redraw shows as a black flash on a display drawn directly; it is
# drawn whole when anything else changes, or something was drawn over it).  Under today's time: the success journal's
# things done today and in the 7 days (success_log.py), read from its files when the screen opens.

# On a touch screen (the watch): the whole panel - today's time in big digits, taller bars, Start / Pause, "-15" and
# Zero (tap it twice) as buttons; a tap on the title (or a swipe right) goes back.
import time
from gfx import Lcd
from screens.base_screen import BaseScreen
from ui.touch import has_touch, TouchList, TouchPanel, Button, header_tapped, button_height, draw_centered
from appconfig import cfg
from i18n import _

_DAY_NAMES = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
_BASELINE_Y = 106
_BAR_MAX_H = 38
_NOTICE_MS = 2000
_CONFIRM_MS = 3000              # the second DEL / tap on Reset must come within this


def _hms(seconds):
    return "%d:%02d:%02d" % (seconds // 3600, (seconds // 60) % 60, seconds % 60)


class FocusStatsScreen(BaseScreen):
    quick_record_from = True        # G0 may start the quick recorder from here

    def __init__(self, app):
        super().__init__(app)
        self._drawn = None
        self._layout = None
        self._notice = None
        self._notice_until = 0
        self._week = None           # the past days, read from the file once per visit
        self._touch = has_touch()
        self._panel = TouchPanel() if self._touch else None
        self._list = TouchList() if self._touch else None

    @property
    def full_height(self):
        return self._touch

    def on_enter(self, **kwargs):
        self._drawn = None
        self._layout = None         # (what the whole screen was drawn for, the renderer's epoch then): see render()
        self._notice = None
        self._week = None
        self._wins = None           # (today, the 7 days) of the success journal, read once per visit
        self._confirm_until = None  # a reset asked for: confirm until then
        self._src = 0
        self._sources = [(_("This device"), None)]
        if not self._touch:
            self._sources += self._peer_sources()

    def _peer_sources(self):
        """[(name, slot)] of the synced devices with statistics, then ("Together", "all"); [] when there are none."""
        try:
            import nuts
            from ble.peers import Peers
            self._peers = Peers(nuts.BASE_DIR + "/ble.json", nuts.BASE_DIR + "/focus/peers")
        except Exception:
            return []
        out = [(n["name"].replace("Squirrel! ", ""), n["slot"]) for n in self._peers.nodes if self._peers.stats(n["slot"])]
        return out + [(_("Together"), "all")] if out else []

    def _days(self, today):
        """The 7 days shown, [(weekday, seconds)], for the chosen source; today's own seconds live."""
        if self._week is None:
            self._week = self.app.focus.week(7)        # the file is read here, once
        src = self._sources[self._src][1]
        out = []
        for i, (key, weekday, secs) in enumerate(self._week):
            mine = today if i == len(self._week) - 1 else secs
            if src is None:
                out.append((weekday, mine))
                continue
            slots = [n["slot"] for n in self._peers.nodes] if src == "all" else [src]
            total = mine if src == "all" else 0
            for slot in slots:
                total += self._peers.stats(slot).get(key, {}).get("focus_min", 0) * 60
            out.append((weekday, total))
        return out

    def _snapshot(self):
        focus = self.app.focus
        return (focus.state, focus.today_seconds())

    def needs_refresh(self):
        if self._notice is not None and time.ticks_diff(time.ticks_ms(), self._notice_until) >= 0:
            return True                              # notice expired: redraw without it
        if self._confirm_until is not None and not self._confirming():
            self._confirm_until = None
            return True                              # the reset was not confirmed: "Reset" again on the watch
        return self._snapshot() != self._drawn

    def _notify(self, text):
        self._notice = text
        self._notice_until = time.ticks_add(time.ticks_ms(), _NOTICE_MS)

    def _take_back(self):
        n = self.app.focus.subtract(cfg.get("FOCUS_UNDO_MIN") * 60)
        self._notify(_("-%d min") % ((n + 59) // 60) if n else _("Nothing to remove"))

    def _reset(self):
        """The first press asks, the second (within _CONFIRM_MS) zeroes today."""
        now = time.ticks_ms()
        if self._confirm_until is None or time.ticks_diff(now, self._confirm_until) >= 0:
            self._confirm_until = time.ticks_add(now, _CONFIRM_MS)
            self._notify(_("Zero? Once more"))
            return
        self._confirm_until = None
        self.app.focus.reset_today()
        self._notify(_("Today zeroed"))

    def _confirming(self):
        return self._confirm_until is not None and time.ticks_diff(time.ticks_ms(), self._confirm_until) < 0

    def _wins_counts(self):
        """(today, the 7 days) of the success journal, read once per visit."""
        if self._wins is None:
            log = getattr(self.app, "success_log", None)
            today = log.today() if log is not None else None
            if today is None:
                self._wins = (0, 0)
            else:
                days = [k for k, _w, _s in self.app.focus.week(7) if k]
                self._wins = (log.count(today), sum(log.count(k) for k in days))
        return self._wins

    def _toggle(self):
        if self.app.focus.toggle() == "no_time":
            self._notice = _("Set time first (Settings)")
            self._notice_until = time.ticks_add(time.ticks_ms(), _NOTICE_MS)

    def handle_input(self, action):
        if self._touch:
            if action in ('ESC', 'LEFT') or (action in ('ENTER', 'OPT') and header_tapped(self.app.keypad)):
                self.app.set_screen("MENU", menu_name="FOCUS")
            else:
                self._panel.handle(action, self.app.keypad)
            return
        if action == 'ESC':
            self.app.set_screen("MENU", menu_name="FOCUS")
        elif action == 'ENTER':
            self._toggle()
        elif action == '-':
            self._take_back()
        elif action == 'DEL':
            self._reset()
        elif action in ('LEFT', 'RIGHT') and len(self._sources) > 1:
            self._src = (self._src + (1 if action == 'RIGHT' else -1)) % len(self._sources)
            self._drawn = None
            self._layout = None

    def _today_color(self, renderer, secs):
        """Today's total in the colour the focus bar has at that progress."""
        goal = self.app.focus.goal_seconds
        bars = getattr(self.app, "bars", None)
        name = bars.focus_color(secs * 100 // goal if goal > 0 else 0) if bars else None
        return renderer._cell_color(name)

    def _render_touch(self, renderer, state, today):
        theme = renderer.theme
        focus = self.app.focus
        w, h = Lcd.screen_size()
        top = TouchList.HEADER
        label = {"running": _("running"), "paused": _("paused"), "stopped": ""}[state]
        self._list.draw_header(theme, _("Focus"), label or None)
        draw_centered(_hms(today), top + 8, 4, self._today_color(renderer, today), theme["BG"])
        draw_centered(_("goal %dh") % (focus.goal_seconds // 3600), top + 44, 1, theme["FG"], theme["BG"])
        if self._week is None:
            self._week = focus.week(7)
        bh = button_height()
        base = h - bh - 26
        bar_max = base - (top + 60)
        col = (w - 8) // 7
        for i, (_key, weekday, secs) in enumerate(self._week):
            if i == len(self._week) - 1:
                secs = today
            x = 4 + i * col
            height = min(bar_max, secs * bar_max // focus.goal_seconds)
            if secs > 0 and height < 1:
                height = 1
            color = theme["WARNING"] if secs >= focus.goal_seconds else (
                theme["ACCENT"] if i == len(self._week) - 1 else theme["FG"])
            if height:
                Lcd.fillRect(x + 3, base - height, col - 6, height, color)
            Lcd.setTextSize(1)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString(_(_DAY_NAMES[weekday]), x + (col - 12) // 2, base + 4)
        Lcd.drawRect(4, base, w - 8, 1, theme["FG"])
        p = self._panel
        p.clear()
        third = (w - 8) // 3
        y = h - bh - 2
        p.add(Button(4, y, third - 4, bh, _("Pause") if state == "running" else _("Start"), "ACCENT"), self._toggle)
        p.add(Button(4 + third, y, third - 4, bh, "-%d" % cfg.get("FOCUS_UNDO_MIN"), "WARNING"), self._take_back)
        p.add(Button(4 + 2 * third, y, third - 4, bh, _("Sure?") if self._confirming() else _("Zero"), "ERROR"),
              self._reset)
        p.draw(theme)
        if self._notice is not None:
            if time.ticks_diff(time.ticks_ms(), self._notice_until) < 0:
                self._list.notice(theme, self._notice[:19], bottom=h - bh - 4)      # above the buttons
            else:
                self._notice = None

    def _today_bar(self, renderer, i, secs):
        """The bar of day `i` (0 = the oldest of the 7), its column blanked first."""
        theme = renderer.theme
        goal = self.app.focus.goal_seconds
        x = 8 + i * 32
        height = min(_BAR_MAX_H, secs * _BAR_MAX_H // goal)
        if secs > 0 and height < 1:
            height = 1
        if secs >= goal:
            color = theme["WARNING"]
        elif i == 6:
            color = theme["ACCENT"]
        else:
            color = theme["FG"]
        Lcd.fillRect(x, _BASELINE_Y - _BAR_MAX_H, 24, _BAR_MAX_H, theme["BG"])
        if height:
            Lcd.fillRect(x, _BASELINE_Y - height, 24, height, color)

    def _today_time(self, renderer, shown):
        Lcd.setTextColor(self._today_color(renderer, shown), renderer.theme["BG"])
        Lcd.setTextSize(2)
        Lcd.drawString(_hms(shown), 5, 20)
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])

    def render(self, renderer):
        theme = renderer.theme
        focus = self.app.focus
        state, today = self._snapshot()
        self._drawn = (state, today)
        if self._touch:
            renderer.clear()
            return self._render_touch(renderer, state, today)
        days = self._days(today)
        shown = days[-1][1] if days else today          # no days: the clock is not set
        layout = (state, self._src, self._notice, focus.goal_seconds, len(_hms(shown)), len(days),
                  theme["FG"], theme["BG"], theme["ACCENT"], theme["WARNING"])
        if self._notice is None and self._layout == (layout, renderer.epoch):
            # only the seconds moved: today's time and bar (the success line under the time is drawn again, as the
            # big digits' cell may reach into it)
            self._today_time(renderer, shown)
            if self._sources[self._src][1] is None:
                self._success_line(renderer)
            self._today_bar(renderer, len(days) - 1, shown)
            return
        renderer.clear()

        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        many = len(self._sources) > 1
        Lcd.drawString("# %s" % self._sources[self._src][0] if many else _("# Focus Stats"), 5, 5)
        label = {"running": _("RUNNING"), "paused": _("PAUSED"), "stopped": _("STOPPED")}[state]
        Lcd.setTextColor(theme["ACCENT"] if state == "running" else theme["WARNING"], theme["BG"])
        Lcd.drawString(label, 235 - 6 * len(label), 5)              # right-aligned, clear of the title

        # the chosen source's days; today's total (in the focus bar's colour)
        self._today_time(renderer, shown)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(_("goal %dh") % (focus.goal_seconds // 3600), 150, 26)
        if self._sources[self._src][1] is None:                          # this device: its success journal too
            self._success_line(renderer)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString(_("[-] -%d min  [DEL] zero today") % cfg.get("FOCUS_UNDO_MIN"), 5, 56)

        # last 7 days, oldest on the left, today on the right
        for i, (weekday, secs) in enumerate(days):
            self._today_bar(renderer, i, secs)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString(_(_DAY_NAMES[weekday]), 8 + i * 32 + 6, _BASELINE_Y + 4)
        Lcd.drawRect(6, _BASELINE_Y, 226, 1, theme["FG"])

        if self._notice is not None:
            if time.ticks_diff(time.ticks_ms(), self._notice_until) < 0:
                renderer.render_alert(self._notice)
            else:
                self._notice = None
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(_("<> device  [ENTER] Start/Pause") if many else _("[ENTER] Start/Pause  [ESC] Back"), 5, 124)
        self._layout = (layout, renderer.epoch)        # after the notice: render_alert() above counts as painted over

    def _success_line(self, renderer):
        wins_today, wins_week = self._wins_counts()
        Lcd.setTextColor(renderer.theme["ACCENT"], renderer.theme["BG"])
        Lcd.drawString(_("successes: today %d, 7 days %d") % (wins_today, wins_week), 5, 44)
