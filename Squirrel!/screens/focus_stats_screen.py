# screens/focus_stats_screen.py - today's focus time and the last 7 days
#
# ENTER  - start / pause the focus timer
# ESC    - back to the main menu
# Redraws once a second while the timer runs (the seconds counter is live).

import time
from gfx import Lcd
from screens.base_screen import BaseScreen

_DAY_NAMES = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
_BASELINE_Y = 106
_BAR_MAX_H = 38
_NOTICE_MS = 2000


def _hms(seconds):
    return "%d:%02d:%02d" % (seconds // 3600, (seconds // 60) % 60, seconds % 60)


class FocusStatsScreen(BaseScreen):
    quick_record_from = True        # G0 may start the quick recorder from here

    def __init__(self, app):
        super().__init__(app)
        self._drawn = None
        self._notice = None
        self._notice_until = 0
        self._week = None           # the past days, read from the file once per visit

    def on_enter(self, **kwargs):
        self._drawn = None
        self._notice = None
        self._week = None

    def _snapshot(self):
        focus = self.app.focus
        return (focus.state, focus.today_seconds())

    def needs_refresh(self):
        if self._notice is not None and time.ticks_diff(time.ticks_ms(), self._notice_until) >= 0:
            return True                              # notice expired: redraw without it
        return self._snapshot() != self._drawn

    def handle_input(self, action):
        if action == 'ESC':
            self.app.set_screen("MENU", menu_name="FOCUS")
        elif action == 'ENTER':
            if self.app.focus.toggle() == "no_time":
                self._notice = "Set time first (Settings)"
                self._notice_until = time.ticks_add(time.ticks_ms(), _NOTICE_MS)

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        focus = self.app.focus
        state, today = self._snapshot()
        self._drawn = (state, today)

        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("# Focus Stats", 5, 5)
        label = {"running": "RUNNING", "paused": "PAUSED", "stopped": "STOPPED"}[state]
        Lcd.setTextColor(theme["ACCENT"] if state == "running" else theme["WARNING"], theme["BG"])
        Lcd.drawString(label, 150, 5)

        # today's total; yellow once the daily goal is reached
        reached = today >= focus.goal_seconds
        Lcd.setTextColor(theme["WARNING"] if reached else theme["FG"], theme["BG"])
        Lcd.setTextSize(2)
        Lcd.drawString(_hms(today), 5, 20)
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("goal %dh" % (focus.goal_seconds // 3600), 150, 26)

        # last 7 days, oldest on the left, today on the right
        if self._week is None:
            self._week = focus.week(7)        # the file is read here, once; today's bar comes from memory below
        week = self._week
        for i, (_key, weekday, secs) in enumerate(week):
            if i == len(week) - 1:
                secs = today
            x = 8 + i * 32
            height = min(_BAR_MAX_H, secs * _BAR_MAX_H // focus.goal_seconds)
            if secs > 0 and height < 1:
                height = 1
            if secs >= focus.goal_seconds:
                color = theme["WARNING"]
            elif i == len(week) - 1:
                color = theme["ACCENT"]
            else:
                color = theme["FG"]
            if height:
                Lcd.fillRect(x, _BASELINE_Y - height, 24, height, color)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString(_DAY_NAMES[weekday], x + 6, _BASELINE_Y + 4)
        Lcd.drawRect(6, _BASELINE_Y, 226, 1, theme["FG"])

        if self._notice is not None:
            if time.ticks_diff(time.ticks_ms(), self._notice_until) < 0:
                renderer.render_alert(self._notice)
            else:
                self._notice = None
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("[ENTER] Start/Pause  [ESC] Back", 5, 124)
