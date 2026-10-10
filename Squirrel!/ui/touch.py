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
