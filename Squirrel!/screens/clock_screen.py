# screens/clock_screen.py
#
# Shortcuts on this screen (modifier keys arrive as ordinary keys here; all of them: docs/guides/en/shortcuts.md):
#   OPT  - start / pause the focus timer          (touch: hold)
#   Aa   - quick sync: every Bluetooth device now (a head; elsewhere Aa opens Mind dump)
#   G0   - quick voice recorder (handled by the app, works from here too)
#   CTRL, then T - a new To-Do;  CTRL, then N - a new note  (CTRL is a key here: it arms the next letter)
#   TAB  - a small menu over the clock: Mind dump, To-Do list, Text notes, Voice notes, Quick sync
#          (TAB / UP / DOWN move, ENTER or the letter in brackets opens; ESC closes it)
#   touch: swipe down - quick sync (the watch: waits for the head, then back here)
#   any other key - open the menu                 (touch: tap)
# On a screen taller than the Cardputer's 135 px (the watch: full_height) the clock is drawn bigger, with the weekday
# and a status line (render_clock_tall); on the Cardputer nothing changes.
import time
from gfx import Lcd, SCREEN_H
from screens.base_screen import BaseScreen
from features import has as _has
from i18n import _

_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

_NOTICE_MS = 1500
_SHORTCUTS = {"t": "TODO", "n": "NOTES"}              # CTRL then T / N: a new one
# The TAB menu: (letter, label, what it opens, the feature it needs).  What it opens: ("screen", name, kwargs)
_QUICK = (
    ("m", "Mind dump", ("MIND_DUMP", {"return_to": ("CLOCK", {})}), "text_edit"),
    ("t", "To-Do list", ("MENU", {"menu_name": "TODO"}), None),
    ("n", "Text notes", ("MENU", {"menu_name": "NOTES"}), "notes"),
    ("v", "Voice notes", ("MENU", {"menu_name": "RECORDS"}), "voice_notes"),
    ("s", "Quick sync", ("BLE_HUB", {"mode": "quick", "back": ("CLOCK", {})}), "ble_hub"),
)
FOCUS_KEY = 'OPT'         # start / pause the focus timer
QUICK_SYNC_KEY = 'Aa'     # quick sync (a head); Mind dump where there is no Bluetooth hub
_FOCUS_MESSAGES = {
    "started": "Focus ON",
    "resumed": "Focus resumed",
    "paused": "Focus paused",
    "no_time": "Set time first!",
}


class ClockScreen(BaseScreen):
    modifiers_as_keys = True
    quick_record_from = True       # G0 may start the quick recorder from this screen
    shows_focus_dot = False        # the main screen has the bars instead
    shows_bars = True              # vertical status bars: battery (left), focus progress (right)
    full_height = True             # the whole panel where there is more of it than the layout area (the watch)

    def __init__(self, app):
        super().__init__(app)
        self._shown_time = None     # HH:MM currently on the display
        self._notice = None         # short message drawn over the clock
        self._notice_until = 0
        self._ctrl = False          # CTRL was pressed: the next letter is a shortcut
        self._quick = None          # TAB menu: the highlighted row, or None when it is closed

    def on_enter(self, **kwargs):
        self._notice = None
        self._ctrl = False
        self._quick = None

    def _notify(self, text):
        self._notice = text
        self._notice_until = time.ticks_add(time.ticks_ms(), _NOTICE_MS)

    def handle_input(self, action):
        if self._quick is not None:
            self._quick_input(action)
            return
        if action == 'CTRL':
            self._ctrl = True                           # CTRL then T / N (CTRL arrives as a key on this screen)
            return
        if self._ctrl:
            self._ctrl = False
            target = _SHORTCUTS.get(action.lower()) if isinstance(action, str) and len(action) == 1 else None
            if target is not None and self._can_write():
                self.app.set_screen("NOTE_EDITOR", menu_name=target, file_index=None)
                return
        if action == 'TAB':
            self._quick = 0 if self._quick_items() else None
            return
        if action in ('FN', 'ALT'):
            return                                      # nothing bound to these here
        if action == FOCUS_KEY:
            self._notify(_(_FOCUS_MESSAGES[self.app.focus.toggle()]))
            return
        if action == QUICK_SYNC_KEY:
            if _has("ble_hub"):
                self.app.set_screen("BLE_HUB", mode="quick", back=("CLOCK", {}))
            elif _has("text_edit"):
                self.app.set_screen("MIND_DUMP", return_to=("CLOCK", {}))
            return
        if action == 'DOWN' and getattr(self.app.keypad, "touch", False) and _has("ble_sync"):
            self.app.set_screen("BLE_SYNC", back=("CLOCK", {}), quick=True)      # the watch: swipe down
            return
        print(f"[NAV] CLOCK -> MENU (MAIN) on key: '{action}'")
        self.app.set_screen("MENU", menu_name="MAIN", fresh=True)

    @staticmethod
    def _can_write():
        return _has("text_edit")

    @staticmethod
    def _quick_items():
        return [q for q in _QUICK if q[3] is None or _has(q[3])]

    def _quick_input(self, action):
        items = self._quick_items()
        letter = action.lower() if isinstance(action, str) and len(action) == 1 else None
        if action in ('ESC', 'LEFT'):
            self._quick = None
        elif action in ('UP', 'DOWN', 'TAB'):
            self._quick = (self._quick + (-1 if action == 'UP' else 1)) % len(items)
        elif action in ('ENTER', 'RIGHT') or letter in [q[0] for q in items]:
            item = items[self._quick] if letter is None else [q for q in items if q[0] == letter][0]
            self._quick = None
            self.app.set_screen(item[2][0], **item[2][1])

    def needs_refresh(self):
        if self._notice is not None and time.ticks_diff(time.ticks_ms(), self._notice_until) >= 0:
            return True                                 # notice expired: redraw without it
        return self.app.rtc.get_time_str() != self._shown_time

    def _status(self):
        """Focus today / the goal, and the battery - the watch's clock shows them in words as well as in the bars:
        (text, colour name) pairs, each in its bar's colour (None: the bar's own, empty colour)."""
        bars = getattr(self.app, "bars", None)
        parts = []
        try:
            done, goal = self.app.focus.today_seconds() // 60, self.app.focus.goal_seconds // 60
            parts.append((_("focus %d:%02d/%d:%02d") % (done // 60, done % 60, goal // 60, goal % 60),
                          bars.focus_color() if bars else None))
        except Exception:
            pass
        level = self.app.battery.level()
        if level is not None:
            parts.append((_("bat %d%%%s") % (level, "+" if self.app.battery.charging else ""),
                          bars.battery_color() if bars else None))
        return parts

    def render(self, renderer):
        date_str = self.app.rtc.get_date_str()
        time_str = self.app.rtc.get_time_str()
        self._shown_time = time_str
        if Lcd.screen_size()[1] > SCREEN_H:
            dt = self.app.rtc.get_datetime()
            renderer.render_clock_tall(date_str, time_str, _(_WEEKDAYS[dt[6] % 7]), self._status())
        else:
            renderer.render_clock(date_str=date_str, time_str=time_str)
        if self._quick is not None:
            self._render_quick(renderer)
        if self._notice is not None:
            if time.ticks_diff(time.ticks_ms(), self._notice_until) < 0:
                renderer.render_options(self._notice)
            else:
                self._notice = None

    def _render_quick(self, renderer):
        """The TAB menu: a small box over the middle of the clock, the letter of each row in brackets."""
        theme = renderer.theme
        items = self._quick_items()
        w, h = Lcd.screen_size()
        bw, bh = 150, 8 + 14 * len(items)
        x, y = (w - bw) // 2, (h - bh) // 2
        Lcd.fillRect(x, y, bw, bh, theme["BG"])
        Lcd.drawRect(x, y, bw, bh, theme["ACCENT"])
        Lcd.setTextSize(1)
        for n, (letter, label, _target, _feature) in enumerate(items):
            selected = n == self._quick
            Lcd.setTextColor(theme["ACCENT"] if selected else theme["FG"], theme["BG"])
            Lcd.drawString("%s%s [%s]" % ("> " if selected else "  ", _(label), letter.upper()), x + 10, y + 5 + 14 * n)
        Lcd.setTextColor(theme["FG"], theme["BG"])
