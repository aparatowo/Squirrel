# screens/personalize_screen.py - Settings -> Personalize
#
# Three levels: the groups -> the settings of a group -> changing one setting.
#   lists    UP / DOWN move, ENTER opens, ESC goes back.
#            DEL (FN + Backspace) on a setting puts its default back.
#   choices  on/off, colours and settings with fixed options are picked from a list:
#            ENTER applies, ESC cancels.  Colours are shown with a sample.
#   numbers and text
#            are typed.  The cursor moves with FN + LEFT / RIGHT, Backspace deletes before it,
#            FN + Backspace after it.  For numbers FN + UP / DOWN change the value by its step.
#            ENTER applies, ESC cancels.
# Every change takes effect at once and is saved to config.txt (see appconfig.py).
#
# Opened from Settings -> Personalize it lists the groups of settings, except the ones that have their own
# place in the menus (Time -> "Time and date", Network -> "Connections").  Those menus open this screen
# restricted to that one group: PersonalizeScreen.on_enter(groups=("Time",), title=..., back=(screen, kwargs)).

import time
from gfx import Lcd
from screens.base_screen import BaseScreen
from appconfig import cfg
from nuts import PALETTE, named_color

_NOTICE_MS = 2500
_VISIBLE = 5                     # rows the menu renderer shows
_RESET_ALL = "Reset all to defaults"
_ELSEWHERE = ("Time", "Network", "Cuckoo")          # groups that are reached from other menus, not from the main list
_SETTINGS_MENU = ("MENU", {"menu_name": "SETTINGS"})
_INT_DIGITS = 6


class PersonalizeScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)
        self._groups = [g for g in cfg.groups() if g not in _ELSEWHERE]
        self._restricted = False
        self._title = "Personalize"
        self._back = _SETTINGS_MENU
        self._reset_state()

    def _reset_state(self):
        self.mode = "groups"         # groups | items | pick | edit | confirm_all
        self.g = 0                   # highlighted group row
        self.g_top = 0
        self.i = 0                   # highlighted setting row
        self.i_top = 0
        self.key = None
        self.options = []            # [(text shown, value)]
        self.p = 0
        self.p_top = 0
        self.buf = ""
        self.cur = 0
        self.error = ""
        self._notice = None
        self._notice_until = 0

    def on_enter(self, groups=None, title=None, back=None, **kwargs):
        self._reset_state()
        self._restricted = bool(groups)
        if groups:
            self._groups = [g for g in cfg.groups() if g in groups]
        else:
            self._groups = [g for g in cfg.groups() if g not in _ELSEWHERE]
        self._title = title or "Personalize"
        self._back = back or _SETTINGS_MENU
        if self._restricted and len(self._groups) == 1:
            self.mode = "items"                          # a single group: straight to its settings

    def on_exit(self):
        self._text_mode(False)

    # ------------------------------------------------------------------ helpers

    def _text_mode(self, on):
        keypad = getattr(self.app, "keypad", None)
        if keypad is not None:
            keypad.set_text_mode(on)

    def _notify(self, text):
        self._notice = text
        self._notice_until = time.ticks_add(time.ticks_ms(), _NOTICE_MS)

    def _group_rows(self):
        rows = ["%s (%d)" % (g, len(cfg.keys_in(g))) for g in self._groups]
        return rows if self._restricted else rows + [_RESET_ALL]

    def _leave(self):
        self.app.set_screen(self._back[0], **self._back[1])

    def _keys(self):
        return cfg.keys_in(self._groups[self.g])

    def _value_text(self, key):
        kind = cfg.describe(key)[0]
        value = cfg.get(key)
        if kind == "bool":
            return "on" if value else "off"
        if kind == "secret":
            return "*" * min(len(value), 8) if value else "(empty)"
        if kind == "text":
            return value if value else "(empty)"
        return str(value)

    def _item_rows(self):
        rows = []
        for key in self._keys():
            label = cfg.describe(key)[2]
            mark = "" if cfg.is_default(key) else "*"        # * = differs from the default
            rows.append("%-18s %s%s" % (label[:18], self._value_text(key)[:10], mark))
        return rows

    @staticmethod
    def _move(index, top, count, delta):
        """Move a highlight with wrap-around, keeping it inside the five visible rows."""
        if count == 0:
            return 0, 0
        index = (index + delta) % count
        if index < top:
            top = index
        elif index >= top + _VISIBLE:
            top = index - _VISIBLE + 1
        return index, max(0, min(top, max(0, count - _VISIBLE)))

    # ------------------------------------------------------------------ input

    def handle_input(self, action):
        if not action:
            return
        if self.mode == "edit":
            self._edit_input(action)
        elif self.mode == "pick":
            self._pick_input(action)
        elif self.mode == "confirm_all":
            if action == 'ENTER':
                for group in self._groups:               # only the settings listed here, not the ones kept in other menus
                    for key in cfg.keys_in(group):
                        cfg.reset(key)
                self._notify("All settings reset")
                self.mode = "groups"
            elif action in ('ESC', 'LEFT'):
                self.mode = "groups"
        elif self.mode == "items":
            self._items_input(action)
        else:
            self._groups_input(action)

    def _groups_input(self, action):
        rows = len(self._groups) + (0 if self._restricted else 1)
        if action == 'UP':
            self.g, self.g_top = self._move(self.g, self.g_top, rows, -1)
        elif action == 'DOWN':
            self.g, self.g_top = self._move(self.g, self.g_top, rows, +1)
        elif action in ('ENTER', 'RIGHT'):
            if self.g == len(self._groups) and not self._restricted:
                self.mode = "confirm_all"
            else:
                self.mode = "items"
                self.i = self.i_top = 0
        elif action in ('ESC', 'LEFT'):
            self._leave()

    def _items_input(self, action):
        keys = self._keys()
        if action == 'UP':
            self.i, self.i_top = self._move(self.i, self.i_top, len(keys), -1)
        elif action == 'DOWN':
            self.i, self.i_top = self._move(self.i, self.i_top, len(keys), +1)
        elif action in ('ENTER', 'RIGHT'):
            self._open_setting(keys[self.i])
        elif action == 'DEL':
            key = keys[self.i]
            if cfg.reset(key):
                self._notify("Default: " + self._value_text(key))
            else:
                self._notify("Already the default")
        elif action in ('ESC', 'LEFT'):
            if self._restricted and len(self._groups) == 1:
                self._leave()
            else:
                self.mode = "groups"

    def _open_setting(self, key):
        kind, _group, _label, extra = cfg.describe(key)
        self.key = key
        current = cfg.get(key)
        if kind in ("bool", "choice", "color"):
            if kind == "bool":
                self.options = [("on", True), ("off", False)]
            elif kind == "color":
                self.options = [(name, name) for name in PALETTE]
            else:
                self.options = [(str(option), option) for option in extra]
            self.p = 0
            for n, (_text, value) in enumerate(self.options):
                if value == current:
                    self.p = n
            self.p_top = max(0, min(self.p - 2, len(self.options) - _VISIBLE))
            self.mode = "pick"
        else:
            self.buf = str(current)
            self.cur = len(self.buf)
            self.error = ""
            self.mode = "edit"
            self._text_mode(True)

    def _pick_input(self, action):
        if action == 'UP':
            self.p, self.p_top = self._move(self.p, self.p_top, len(self.options), -1)
        elif action == 'DOWN':
            self.p, self.p_top = self._move(self.p, self.p_top, len(self.options), +1)
        elif action == 'ENTER':
            cfg.set(self.key, self.options[self.p][1])
            self._notify("Saved")
            self.mode = "items"
        elif action in ('ESC', 'LEFT'):
            self.mode = "items"

    def _leave_edit(self, notice=None):
        self._text_mode(False)
        self.mode = "items"
        if notice:
            self._notify(notice)

    def _insert(self, char):
        kind, _group, _label, extra = cfg.describe(self.key)
        if kind == "int":
            if len(self.buf) >= _INT_DIGITS:
                return
            if not (char.isdigit() or (char == '-' and self.cur == 0 and '-' not in self.buf)):
                return
        elif len(self.buf) >= extra:
            return
        self.buf = self.buf[:self.cur] + char + self.buf[self.cur:]
        self.cur += 1

    def _edit_input(self, action):
        kind, _group, _label, extra = cfg.describe(self.key)
        if action == 'ESC':
            self._leave_edit()
            return
        if action == 'ENTER':
            self._apply_edit(kind)
            return
        self.error = ""
        if action == 'LEFT':
            self.cur = max(0, self.cur - 1)
        elif action == 'RIGHT':
            self.cur = min(len(self.buf), self.cur + 1)
        elif action == 'BACKSPACE':
            if self.cur > 0:
                self.buf = self.buf[:self.cur - 1] + self.buf[self.cur:]
                self.cur -= 1
        elif action == 'DEL':
            if self.cur < len(self.buf):
                self.buf = self.buf[:self.cur] + self.buf[self.cur + 1:]
        elif kind == "int" and action in ('UP', 'DOWN'):
            try:
                number = int(self.buf)
            except ValueError:
                number = cfg.get(self.key)
            number += extra[2] if action == 'UP' else -extra[2]
            self.buf = str(cfg.validate(self.key, number))
            self.cur = len(self.buf)
        elif action == 'SPACE':
            self._insert(" ")
        elif len(action) == 1:
            self._insert(action)

    def _apply_edit(self, kind):
        if kind == "int":
            try:
                number = int(self.buf)
            except ValueError:
                self.error = "Type a whole number"
                return
            value = cfg.validate(self.key, number)
            notice = "Saved" if value == number else "Limited to %d" % value
        else:
            value = self.buf
            notice = "Saved"
        cfg.set(self.key, value)
        self._leave_edit(notice)

    # ------------------------------------------------------------------ drawing

    def needs_refresh(self):
        return self._notice is not None and time.ticks_diff(time.ticks_ms(), self._notice_until) >= 0

    def render(self, renderer):
        if self.mode == "edit":
            self._render_edit(renderer)
        elif self.mode == "confirm_all":
            self._render_confirm(renderer)
        elif self.mode == "pick":
            label = cfg.describe(self.key)[2]
            renderer.render_menu(label, [text for text, _v in self.options], self.p, self.p_top, _VISIBLE)
            if cfg.describe(self.key)[0] == "color":
                for row, (_text, name) in enumerate(self.options[self.p_top:self.p_top + _VISIBLE]):
                    Lcd.fillRect(205, 40 + 15 * row, 24, 9, named_color(name))
        elif self.mode == "items":
            title = self._title if (self._restricted and len(self._groups) == 1) else self._groups[self.g]
            renderer.render_menu(title, self._item_rows(), self.i, self.i_top, _VISIBLE)
        else:
            renderer.render_menu(self._title, self._group_rows(), self.g, self.g_top, _VISIBLE)
        if self._notice is not None and self.mode in ("groups", "items", "pick"):
            if time.ticks_diff(time.ticks_ms(), self._notice_until) < 0:
                renderer.render_options(self._notice)
            else:
                self._notice = None

    def _render_confirm(self, renderer):
        renderer.clear()
        theme = renderer.theme
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["ERROR"], theme["BG"])
        Lcd.drawString("# Reset ALL settings?", 5, 5)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("Every setting goes back to", 5, 35)
        Lcd.drawString("its default value.", 5, 49)
        Lcd.setTextColor(theme["WARNING"], theme["BG"])
        Lcd.drawString("[ENTER] Reset   [ESC] Cancel", 5, 100)

    def _render_edit(self, renderer):
        kind, _group, label, extra = cfg.describe(self.key)
        renderer.clear()
        theme = renderer.theme
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("# " + label[:26], 5, 5)
        renderer.render_keypad_mode_indicator(getattr(self.app, "keypad", None))
        if kind == "int":
            hint = "%d to %d   default %s" % (extra[0], extra[1], cfg.default(self.key))
        elif kind == "secret":
            hint = "hidden   up to %d characters" % extra
        else:
            hint = "up to %d characters" % extra
        Lcd.drawString(hint[:38], 5, 22)
        Lcd.drawRect(5, 38, 230, 28, theme["ACCENT"])
        shown = "*" * len(self.buf) if kind == "secret" else self.buf
        start = max(0, self.cur - 34)                         # keep the cursor inside the 36-character box
        line = shown[start:self.cur] + "|" + shown[self.cur:start + 35]
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(line, 10, 48)
        if self.error:
            Lcd.setTextColor(theme["ERROR"], theme["BG"])
            Lcd.drawString(self.error, 5, 76)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("[ENTER] Save  [ESC] Cancel", 5, 104)
        Lcd.drawString("FN + arrows: cursor" + ("  and +/-" if kind == "int" else ""), 5, 118)
