# screens/wifi_screen.py - Settings -> WiFi networks
#
# The networks the device may join, kept in nuts.WIFI_PROFILES_FILE (see wifi_profiles.py).  When
# the time is set over WiFi the strongest of them that is in range is used; UIFlow's own saved
# network and the WIFI_SSID setting stay available as a fallback, and the other way round.
#
#   list     UP / DOWN move, ENTER edits (or adds, on the first row), ESC back.
#            DEL (FN+Backspace) deletes: press it three more times to confirm, ESC cancels.
#   editing  two steps: the name, then the password (shown as asterisks).  ENTER moves on / saves,
#            ESC cancels.  The cursor moves with FN + LEFT / RIGHT.

import time
from gfx import Lcd
import nuts
from screens.base_screen import BaseScreen
from line_editor import LineEditor
from wifi_profiles import WifiProfiles, MAX_SSID, MAX_PASSWORD, MAX_NETWORKS

_ADD = "+ [Add network]"
_VISIBLE = 5
_NOTICE_MS = 2500
_DELETE_PRESSES = 3


class WifiScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)
        self._profiles = None
        self._reset()

    def _reset(self):
        self.mode = "list"            # list | name | password
        self.sel = 0
        self.top = 0
        self._index = None            # which saved network is being edited; None = a new one
        self._editor = None
        self._name = ""
        self.error = ""
        self._delete = None           # presses still needed to confirm a deletion
        self._notice = None
        self._notice_until = 0

    def on_enter(self, **kwargs):
        self._reset()
        self._profiles = WifiProfiles(nuts.WIFI_PROFILES_FILE)

    def on_exit(self):
        self._text_mode(False)

    def _text_mode(self, on):
        keypad = getattr(self.app, "keypad", None)
        if keypad is not None:
            keypad.set_text_mode(on)

    def _notify(self, text):
        self._notice = text
        self._notice_until = time.ticks_add(time.ticks_ms(), _NOTICE_MS)

    def _rows(self):
        return [_ADD] + [ssid for ssid, _pw in self._profiles.all()]

    def _move(self, delta):
        count = len(self._rows())
        self.sel = (self.sel + delta) % count
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + _VISIBLE:
            self.top = self.sel - _VISIBLE + 1
        self.top = max(0, min(self.top, max(0, count - _VISIBLE)))

    # ------------------------------------------------------------------ input

    def handle_input(self, action):
        if not action:
            return
        if self.mode == "list":
            self._list_input(action)
        else:
            self._edit_input(action)

    def _list_input(self, action):
        if self._delete is not None:
            self._delete_input(action)
        elif action == 'UP':
            self._move(-1)
        elif action == 'DOWN':
            self._move(+1)
        elif action in ('ENTER', 'RIGHT'):
            self._open_row()
        elif action == 'DEL' and self.sel > 0:
            self._delete = _DELETE_PRESSES
        elif action in ('ESC', 'LEFT'):
            self.app.set_screen("MENU", menu_name="CONNECTIONS")

    def _open_row(self):
        if self.sel == 0:
            if self._profiles.is_full():
                self._notify("List full (%d)" % MAX_NETWORKS)
                return
            self._index, name, password = None, "", ""
        else:
            self._index = self.sel - 1
            name, password = self._profiles.all()[self._index]
        self._name = name
        self._password = password
        self._editor = LineEditor(name, MAX_SSID)
        self.error = ""
        self.mode = "name"
        self._text_mode(True)

    def _delete_input(self, action):
        if action == 'DEL':
            self._delete -= 1
            if self._delete <= 0:
                self._delete = None
                self._profiles.delete(self.sel - 1)
                self._move(0)
                self.sel = min(self.sel, len(self._rows()) - 1)
                self._notify("Deleted")
        else:
            self._delete = None                  # ESC or any other key cancels

    def _edit_input(self, action):
        if action == 'ESC':
            self._finish_edit()
            return
        if action == 'ENTER':
            if self.mode == "name":
                name = self._editor.buf.strip()
                if not name:
                    self.error = "The name is required"
                    return
                self._name = name
                self._editor = LineEditor(self._password, MAX_PASSWORD, secret=True)
                self.error = ""
                self.mode = "password"
            else:
                self._save()
            return
        self.error = ""
        self._editor.handle(action)

    def _save(self):
        password = self._editor.buf
        if self._index is None:
            known = any(ssid == self._name for ssid, _pw in self._profiles.all())
            if not self._profiles.add(self._name, password):
                self._finish_edit("Not saved")
                return
            self._finish_edit("Updated" if known else "Saved")
        else:
            ok = self._profiles.update(self._index, self._name, password)
            self._finish_edit("Saved" if ok else "Not saved")

    def _finish_edit(self, notice=None):
        self._text_mode(False)
        self.mode = "list"
        self._editor = None
        self.sel = min(self.sel, len(self._rows()) - 1)
        self._move(0)
        if notice:
            self._notify(notice)

    # ------------------------------------------------------------------ drawing

    def needs_refresh(self):
        return self._notice is not None and time.ticks_diff(time.ticks_ms(), self._notice_until) >= 0

    def render(self, renderer):
        if self.mode == "list":
            renderer.render_menu("WiFi networks", self._rows(), self.sel, self.top, _VISIBLE)
            if self._delete is not None:
                renderer.render_delete_confirm(self._delete, self._rows()[self.sel])
            elif self._notice is not None:
                if time.ticks_diff(time.ticks_ms(), self._notice_until) < 0:
                    renderer.render_options(self._notice)
                else:
                    self._notice = None
        else:
            self._render_edit(renderer)

    def _render_edit(self, renderer):
        renderer.clear()
        theme = renderer.theme
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("# " + ("New network" if self._index is None else "Edit network"), 5, 5)
        renderer.render_keypad_mode_indicator(getattr(self.app, "keypad", None))
        Lcd.drawString("Name" if self.mode == "name" else "Password for " + self._name[:16], 5, 22)
        Lcd.drawRect(5, 38, 230, 28, theme["ACCENT"])
        Lcd.drawString(self._editor.view(35), 10, 48)
        if self.error:
            Lcd.setTextColor(theme["ERROR"], theme["BG"])
            Lcd.drawString(self.error, 5, 76)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("[ENTER] " + ("Next" if self.mode == "name" else "Save") + "  [ESC] Cancel", 5, 104)
        Lcd.drawString("FN + arrows: cursor", 5, 118)
