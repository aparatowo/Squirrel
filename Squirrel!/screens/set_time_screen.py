# screens/set_time_screen.py — Manual time-setting screen
#
# Five fields: YYYY / MM / DD / HH / MM.  The model (the values, wrapping, the length of the month, saving) is the same
# for every device; there are two views:
#   with a keyboard (the Cardputer):  LEFT / RIGHT field, UP / DOWN value, ENTER save, ESC cancel;
#   with a touch screen (ui/touch.py): a "+" above and a "-" below every field, Cancel / Save at the bottom, sized in
#   millimetres on the whole panel (full_height) - hold "+" / "-" and the value keeps changing, faster and faster;
#   UP / DOWN still change the field touched last, ESC (swipe right, the side button) cancels.
# The time is written to the device's hardware clock too (RTCManager.set_manual).

import time
from gfx import Lcd
from screens.base_screen import BaseScreen
from timeutil import days_from_civil, weekday_from_days
from ui.touch import Button, TouchPanel, has_touch, mm, MIN_TARGET_MM

_DAYS_IN_MONTH = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _days_in(year, month):
    if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        return 29
    return _DAYS_IN_MONTH[month]


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
        self._panel = TouchPanel() if has_touch() else None
        self._layout = None       # touch: (column width, value label y, value y)

    @property
    def full_height(self):
        """A touch screen gets the whole panel: room for buttons a finger can hit."""
        return self._panel is not None

    def _step(self, field, delta):
        label, lo, hi = _FIELDS[field]
        v = self._values[field] + delta
        self._values[field] = lo + (v - lo) % (hi - lo + 1)          # wraps around, like UP / DOWN
        y, m = self._values[0], self._values[1]
        self._values[2] = min(self._values[2], _days_in(y, m))       # 31 -> 30 when the month changes
        self._field = field

    def _build_touch(self):
        """The widgets, from the size of the screen and millimetres."""
        w, h = Lcd.screen_size()
        gap = 4
        title_h = 22
        btn_h = max(mm(MIN_TARGET_MM), 24)
        value_h = 8 + 4 + 16                                          # the label (size 1) and the value (size 2)
        step_h = max(20, (h - title_h - btn_h - value_h - 4 * gap) // 2)
        col = w // len(_FIELDS)
        plus_y = title_h
        value_y = plus_y + step_h + gap
        minus_y = value_y + value_h + gap
        btn_y = h - btn_h
        p = self._panel
        p.clear()
        self._buttons = []                                            # per field: (its "+", its "-")
        for i in range(len(_FIELDS)):
            x = i * col
            plus = p.add(Button(x + 2, plus_y, col - 4, step_h, "+"), lambda i=i: self._step(i, 1), repeat=True)
            minus = p.add(Button(x + 2, minus_y, col - 4, step_h, "-"), lambda i=i: self._step(i, -1), repeat=True)
            self._buttons.append((plus, minus))
        half = w // 2
        p.add(Button(2, btn_y, half - 6, btn_h, "Cancel", "ERROR"), self._cancel)
        p.add(Button(half + 4, btn_y, half - 6, btn_h, "Save", "ACCENT"), self._save)
        self._layout = (col, value_y, value_y + 12)

    def _cancel(self):
        self.app.set_screen("MENU", menu_name="TIME_DATE")

    def on_enter(self, **kwargs):
        # Pre-fill with current time so user corrects rather than resets
        try:
            dt = self.app.rtc.get_datetime()
            self._values = [dt[0], dt[1], dt[2], dt[3], dt[4]]
        except Exception:
            self._values = [2026, 1, 1, 0, 0]
        self._field = 0
        if self._panel is not None:
            self._build_touch()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def needs_refresh(self):
        return self._panel is not None and self._panel.tick(self.app.keypad)

    def handle_input(self, action):
        if action == 'ESC':
            self.app.set_screen("MENU", menu_name="TIME_DATE")
            return

        if self._panel is not None and self._panel.handle(action, self.app.keypad):
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
        mday = min(mday, _days_in(year, month))
        # the weekday matters (routines by day of the week); it used to be saved as 0 = Monday whatever the date
        dt = (year, month, mday, hour, minute, 0, weekday_from_days(days_from_civil(year, month, mday)), 0)
        self.app.rtc.set_manual(dt)
        self.app.renderer.render_options("Time Set!")
        time.sleep(0.8)
        self.app.set_screen("MENU", menu_name="TIME_DATE")

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, renderer):
        if self._panel is not None:
            return self._render_touch(renderer)
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

    def _render_touch(self, renderer):
        renderer.clear()
        theme = renderer.theme
        col, label_y, value_y = self._layout
        Lcd.setTextSize(2)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("Set Time", 4, 2)
        active = self._buttons[self._field]
        self._panel.draw(theme, lambda wdg: wdg in active)
        for i, (label, _, _) in enumerate(_FIELDS):
            x = i * col
            c = theme["ACCENT"] if i == self._field else theme["FG"]
            Lcd.setTextColor(c, theme["BG"])
            Lcd.setTextSize(1)
            Lcd.drawString(label, x + (col - 6 * len(label)) // 2, label_y)
            text = ("%04d" if i == 0 else "%02d") % self._values[i]
            Lcd.setTextSize(2)
            Lcd.drawString(text, x + (col - 12 * len(text)) // 2, value_y)
