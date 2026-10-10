# touch.py - widgets for touch screens, the same on every device with a touch screen
#
# A screen made for touch builds its widgets from the size it gets (gfx.Lcd.screen_size(); set full_height = True on
# the screen to get the whole panel) and from millimetres (mm(): the port's [display] ppi), so it fits another watch
# with another panel without changes.  It hands the actions to its TouchPanel, which looks at WHERE the input says the
# finger was (TouchInput.tap_xy / touch_xy, hw/touch_input.py):
#
#   panel = TouchPanel()
#   panel.add(Button(...), on_tap=save)
#   panel.add(minus_button, on_tap=lambda: change(-1), repeat=True)    # held: keeps changing, faster and faster
#   handle_input(action):   if panel.handle(action, app.keypad): ...   (True: a widget took it)
#   needs_refresh():        return panel.tick(app.keypad)
#   render():               panel.draw(theme)
#
# Whether the device has a touch screen at all: has_touch() (port.toml [input] touch = true).
import time
import port_config as _P
from gfx import Lcd

PX_PER_MM = getattr(_P, "DISPLAY_PPI", 160) / 25.4
MIN_TARGET_MM = 6                       # the smallest a finger hits reliably (6-7 mm; Apple: 44 pt, Android: 48 dp)
REPEAT_FIRST_MS, REPEAT_MIN_MS, REPEAT_SPEEDUP = 300, 60, 0.75


def mm(v):
    """Millimetres -> pixels on this device's panel."""
    return int(v * PX_PER_MM + 0.5)


def has_touch():
    return "input.touch" in _P.HARDWARE


class Button:
    """A rectangle with a centred label.  color: a theme key ("FG", "ACCENT", "ERROR" ...)."""

    def __init__(self, x, y, w, h, label, color="FG", size=2):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.label, self.color, self.size = label, color, size

    def hit(self, xy):
        return xy is not None and self.x <= xy[0] < self.x + self.w and self.y <= xy[1] < self.y + self.h

    def draw(self, theme, active=False):
        col = theme["ACCENT"] if active else theme[self.color]
        Lcd.drawRect(self.x, self.y, self.w, self.h, col)
        size = self.size
        while size > 1 and (6 * size * len(self.label) > self.w - 4 or 8 * size > self.h - 2):
            size -= 1                                            # the label always fits its button
        Lcd.setTextSize(size)
        Lcd.setTextColor(col, theme["BG"])
        Lcd.drawString(self.label, self.x + (self.w - 6 * size * len(self.label)) // 2, self.y + (self.h - 8 * size) // 2)


class TouchPanel:
    """The widgets of one screen: which one a tap hits, hold-to-repeat, drawing them."""

    def __init__(self):
        self._items = []                        # [widget, on_tap, repeat]
        self._hold = None                       # [item, when the next step is due (ticks), interval ms]
        self.active = None                      # the widget touched last (drawn highlighted when asked)

    def clear(self):
        self._items, self._hold, self.active = [], None, None

    def add(self, widget, on_tap, repeat=False):
        self._items.append([widget, on_tap, repeat])
        return widget

    def _at(self, xy):
        for item in self._items:
            if item[0].hit(xy):
                return item
        return None

    def handle(self, action, keypad):
        """A tap (ENTER) on a widget runs its on_tap; a long press (OPT) on a repeating one runs it and keeps running it
        while held (see tick).  Returns True when a widget took the action."""
        if action not in ("ENTER", "OPT"):
            return False
        item = self._at(getattr(keypad, "tap_xy", None))
        if item is None:
            return False
        self.active = item[0]
        if action == "ENTER" or item[2]:
            item[1]()
        if action == "OPT" and item[2]:
            self._hold = [item, time.ticks_add(time.ticks_ms(), REPEAT_FIRST_MS), REPEAT_FIRST_MS]
        return True

    def tick(self, keypad):
        """Call from needs_refresh(): the next step of a held repeating widget.  True when it stepped (redraw)."""
        h = self._hold
        if h is None:
            return False
        if not h[0][0].hit(getattr(keypad, "touch_xy", None)):
            self._hold = None                                    # lifted, or moved off the widget
            return False
        now = time.ticks_ms()
        if time.ticks_diff(now, h[1]) < 0:
            return False
        h[0][1]()
        h[2] = max(REPEAT_MIN_MS, int(h[2] * REPEAT_SPEEDUP))
        h[1] = time.ticks_add(now, h[2])
        return True

    def draw(self, theme, highlight=None):
        """Draw every widget; those for which highlight(widget) is true in the accent colour."""
        for widget, _cb, _rep in self._items:
            widget.draw(theme, bool(highlight and highlight(widget)))


class TouchList:
    """A list on the whole panel: a title (tap = back) and rows of at least MIN_TARGET_MM (tap = choose).  The screen
    keeps the highlight and the first row shown; UP / DOWN (swipes) move the highlight, move() keeps it in view.

        lst = TouchList()
        hit = lst.hit(keypad.tap_xy, top, count)     # "back", a row index or None
        lst.draw_header(theme, title, "3/9")
        lst.draw_row(theme, row, text, selected, sub="on")   # sub: a second line (the value of a setting)
    """
    HEADER = 30

    def __init__(self):
        from gfx import PANEL_H
        self.row_h = max(mm(MIN_TARGET_MM), 24)
        self.visible = max(1, (PANEL_H - self.HEADER) // self.row_h)

    def y_of(self, row):
        return self.HEADER + row * self.row_h

    def hit(self, xy, top, count):
        if xy is None:
            return None
        if xy[1] < self.HEADER:
            return "back"
        index = top + (xy[1] - self.HEADER) // self.row_h
        return index if 0 <= index < count else None

    def move(self, index, top, count, delta):
        """The highlight one row on (with wrap-around), kept among the visible rows.  Returns (index, top)."""
        if count == 0:
            return 0, 0
        index = (index + delta) % count
        if index < top:
            top = index
        elif index >= top + self.visible:
            top = index - self.visible + 1
        return index, max(0, min(top, count - self.visible))

    def draw_header(self, theme, title, pos=None):
        w = Lcd.screen_size()[0]
        Lcd.setTextSize(2)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("<", 4, 7)
        room = (w - 26 - (6 * len(pos) + 6 if pos else 0)) // 12
        Lcd.drawString(title[:room], 22, 7)
        if pos:
            Lcd.setTextSize(1)
            Lcd.drawString(pos, w - 4 - 6 * len(pos), 11)
        Lcd.drawLine(0, self.HEADER - 2, w - 1, self.HEADER - 2, theme["FG"])

    def draw_row(self, theme, row, text, selected, sub=None, sub_color="ACCENT"):
        """One row: size-2 text, centred in the row, or with `sub` a second line under it, right-aligned."""
        w = Lcd.screen_size()[0]
        y, h = self.y_of(row), self.row_h
        bg = theme["PANEL_BG"] if selected else theme["BG"]
        if selected:
            Lcd.fillRect(0, y + 1, w, h - 2, bg)
        Lcd.setTextSize(2)
        Lcd.setTextColor(theme["ACCENT"] if selected else theme["FG"], bg)
        cols = (w - 8) // 12
        if sub is None:
            Lcd.drawString(text[:cols], 4, y + (h - 16) // 2)
            return
        gap = (h - 32) // 3
        Lcd.drawString(text[:cols], 4, y + gap)
        sub = sub[:cols]
        Lcd.setTextColor(theme[sub_color], bg)
        Lcd.drawString(sub, w - 4 - 12 * len(sub), y + 2 * gap + 16)

    def notice(self, theme, text):
        """A message over the bottom of the list (what was saved ...)."""
        w, h = Lcd.screen_size()
        Lcd.fillRect(0, h - 28, w, 28, theme["WARNING"])
        Lcd.setTextSize(2)
        Lcd.setTextColor(theme["BG"], theme["WARNING"])
        text = text[:(w - 8) // 12]
        Lcd.drawString(text, (w - 12 * len(text)) // 2, h - 22)
