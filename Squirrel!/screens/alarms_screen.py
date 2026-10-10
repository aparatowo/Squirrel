# screens/alarms_screen.py - "Upcoming alarms": what will wake the device from a deep sleep, earliest first
#
# The coming routines, cuckoo calls and snoozed routines (alarms.py), and the one the next deep sleep would write into
# the clock.  Only where the clock has an alarm (features.toml: deep_sleep).  ESC / a tap on the title: back.
import time
from gfx import Lcd
from screens.base_screen import BaseScreen
from ui.touch import has_touch

_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class AlarmsScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)
        self._touch = has_touch()
        self._shown_minute = None

    @property
    def full_height(self):
        return self._touch

    def on_enter(self, **kwargs):
        self._shown_minute = None

    def handle_input(self, action):
        if action in ('ESC', 'LEFT') or (action == 'ENTER' and self._touch):
            self.app.set_screen("MENU", menu_name="TIME_DATE")

    def needs_refresh(self):
        return time.localtime()[4] != self._shown_minute          # the list moves on every minute

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        w, h = Lcd.screen_size()
        self._shown_minute = time.localtime()[4]
        big = 2 if self._touch else 1
        Lcd.setTextSize(big)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(("< " if self._touch else "") + "Upcoming alarms", 4, 6)
        events = self.app.alarms.upcoming(n=12)
        nxt = self.app.deep_sleep.next_alarm() if self.app.deep_sleep is not None else None
        row = 18 if big == 2 else 12
        y = 34 if big == 2 else 22
        Lcd.setTextSize(1)
        if self.app.cfg_sleep_mode() != "deep":
            Lcd.setTextColor(theme["WARNING"], theme["BG"])
            Lcd.drawString("Sleep mode is not 'deep' (Personalize)", 4, y)
            y += 12
        if not events:
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString("Nothing planned: routines, cuckoo", 4, y)
            return
        for at, label in events:
            if y + row > h:
                break
            t = time.localtime(at)
            when = "%s %02d:%02d" % (_WEEKDAYS[t[6]], t[3], t[4])
            first = nxt is not None and at <= nxt[0] < at + 60
            Lcd.setTextColor(theme["ACCENT"] if first else theme["FG"], theme["BG"])
            Lcd.setTextSize(big)
            Lcd.drawString(when, 4, y)
            Lcd.setTextSize(1)
            Lcd.drawString(label[:(w - 4 - 6 * 9 * big) // 6], 8 + 6 * 9 * big, y + (big - 1) * 4)
            y += row
