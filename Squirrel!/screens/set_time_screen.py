# screens/set_time_screen.py — Manual time-setting screen
#
# Displays five fields: YYYY / MM / DD / HH / MM
# LEFT / RIGHT  — move between fields
# UP / DOWN     — increment / decrement current field value
# ENTER         — confirm and save to RTC
# ESC           — cancel and return to Settings

import time
from gfx import Lcd
from screens.base_screen import BaseScreen


# Field definitions: (label, min_value, max_value)
_FIELDS = [
    ("YEAR", 2024, 2099),
    ("MON",     1,   12),
    ("DAY",     1,   31),
    ("HOUR",    0,   23),
    ("MIN",     0,   59),
]


class SetTimeScreen(BaseScreen):
    """Manual time entry screen.

    Reads the current soft-RTC time as initial values so the user only
    needs to correct whatever is wrong, not retype everything.
    """

    def __init__(self, app):
        super().__init__(app)
        self._values = [2026, 1, 1, 0, 0]
        self._field = 0   # active field index

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self, **kwargs):
        # Pre-fill with current time so user corrects rather than resets
        try:
            dt = self.app.rtc.get_datetime()
            self._values = [dt[0], dt[1], dt[2], dt[3], dt[4]]
        except Exception:
            self._values = [2026, 1, 1, 0, 0]
        self._field = 0

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, action):
        if action == 'ESC':
            self.app.set_screen("MENU", menu_name="TIME_DATE")
            return

        if action == 'LEFT':
            self._field = max(0, self._field - 1)

        elif action == 'RIGHT':
            self._field = min(len(_FIELDS) - 1, self._field + 1)

        elif action == 'UP':
            label, lo, hi = _FIELDS[self._field]
            self._values[self._field] = lo if self._values[self._field] >= hi \
                else self._values[self._field] + 1

        elif action == 'DOWN':
            label, lo, hi = _FIELDS[self._field]
            self._values[self._field] = hi if self._values[self._field] <= lo \
                else self._values[self._field] - 1

        elif action == 'ENTER':
            self._save()

    def _save(self):
        year, month, mday, hour, minute = self._values
        # Clamp day to valid range for chosen month (rough check)
        days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        mday = min(mday, days_in_month[month])

        dt = (year, month, mday, hour, minute, 0, 0, 0)
        self.app.rtc.set_manual(dt)
        self.app.renderer.render_options("Time Set!")
        time.sleep(0.8)
        self.app.set_screen("MENU", menu_name="TIME_DATE")

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        fonts = renderer.fonts

        Lcd.setTextSize(fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("# Set Time", 5, 5)
        Lcd.drawString("L/R: field  U/D: value", 5, 18)

        # Draw five fields in a row, highlight the active one
        field_x  = [5, 55, 105, 150, 195]
        field_y  = 50
        value_y  = 75

        for i, (label, _, _) in enumerate(_FIELDS):
            x = field_x[i]
            # Separator between date and time
            if i == 3:
                Lcd.setTextColor(theme["FG"], theme["BG"])
                Lcd.drawString("|", x - 6, value_y)

            if i == self._field:
                Lcd.setTextColor(theme["ACCENT"], theme["BG"])
                Lcd.drawRect(x - 2, field_y - 3, 43, 38, theme["ACCENT"])
            else:
                Lcd.setTextColor(theme["FG"], theme["BG"])

            Lcd.drawString(label, x, field_y)

            if i in (0,):   # year: 4 digits
                val_str = f"{self._values[i]:04d}"
            else:
                val_str = f"{self._values[i]:02d}"

            Lcd.drawString(val_str, x + 4, value_y)

        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("[ENTER] Save | [ESC] Cancel", 5, 115)