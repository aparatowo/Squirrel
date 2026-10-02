# screens/font_test_screen.py - Settings -> Experimental -> Font test
#
# Tries the .vlw font with the Polish letters, safely.  A font that turns out to be unusable can leave the screen
# blank or garbled, and then nothing could be pressed to switch it off - so:
#   * the font is never loaded behind your back: only ENTER here loads it (FONT_ENABLED stays off);
#   * you then have TRY_SECONDS to press OPT = "keep it": only that saves FONT_ENABLED and makes the font load
#     at every start.  Any other key, or no key at all, restarts the device and nothing has changed;
#   * if a saved font ever misbehaves, hold G0 while the device starts: that start skips the font.
#
# While no font is loaded, text with Polish letters is drawn as plain letters (ą -> a), see gfx.py.

import os
import time
import nuts
from gfx import Lcd
from boot_log import log
from appconfig import cfg
from screens.base_screen import BaseScreen

TRY_SECONDS = 15

SAMPLES = ("Zażółć gęślą jaźń", "ĄĆĘŁŃÓŚŹŻ ąćęłńóśźż", "Ä Ö Ü ß é è ç ñ € …")
RULER = "0123456789" * 3 + "012345"          # 36 characters: must end exactly at the right edge of the box


class FontTestScreen(BaseScreen):
    modifiers_as_keys = True          # OPT arrives as a key
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self.state = "idle"           # idle | trying | restarting
        self.message = ""
        self._deadline = 0
        self._drawn = None
        self._restart = None          # set by tests; the real one is machine.reset

    def on_enter(self, **kwargs):
        self.state = "idle"
        self.message = ""
        self._drawn = None

    # ------------------------------------------------------------------ actions

    def _do_restart(self):
        self.state = "restarting"
        log("[FONT] restarting")
        try:
            self.app.renderer.render_options("Restarting...")
        except Exception:
            pass
        time.sleep(0.4)
        if self._restart is not None:
            self._restart()
            return
        import machine
        machine.reset()

    def handle_input(self, action):
        if self.state == "restarting":
            return
        if self.state == "trying":
            if action == 'OPT':
                cfg.set("FONT_ENABLED", True)
                self.state = "idle"
                self.message = "Kept: used at every start"
                log("[FONT] accepted by the user")
            else:
                self._do_restart()                 # undo: the font is only gone after a restart
            return
        if action == 'ESC':
            self.app.set_screen("MENU", menu_name="EXPERIMENTAL")
        elif action == 'ENTER':
            if Lcd.font_active:
                cfg.set("FONT_ENABLED", False)     # switching it off also needs a restart
                self._do_restart()
            elif Lcd.load_font(nuts.FONT_FILES):
                self.state = "trying"
                self._deadline = time.ticks_add(time.ticks_ms(), TRY_SECONDS * 1000)
                self.message = ""
            else:
                self.message = "Not loaded: " + Lcd.last_error

    def _seconds_left(self):
        left = time.ticks_diff(self._deadline, time.ticks_ms())
        return max(0, (left + 999) // 1000)

    def needs_refresh(self):
        # The countdown lives here: this is called on every pass of the main loop.
        if self.state == "trying":
            if self._seconds_left() <= 0:
                self._do_restart()
                return False
            return self._seconds_left() != self._drawn
        return False

    # ------------------------------------------------------------------ drawing

    def _file_line(self):
        path = Lcd.find_font(nuts.FONT_FILES)
        if path is None:
            return "File: not found (fonts/squirrel.vlw)"
        try:
            return "File: %d bytes" % os.stat(path)[6]
        except OSError:
            return "File: found"

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("Font test", 5, 4)
        Lcd.setTextColor(theme["ACCENT"] if Lcd.font_active else theme["WARNING"], theme["BG"])
        Lcd.drawString("Font in use" if Lcd.font_active else "No font loaded: plain letters", 5, 18)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(self._file_line(), 5, 32)
        y = 46
        for sample in SAMPLES:
            Lcd.drawString(sample, 5, y)
            y += 13
        Lcd.drawString(RULER, 5, y)
        Lcd.drawRect(4, y - 1, 6 * len(RULER) + 3, 12, theme["ACCENT"])
        layout = cfg.get("KEYBOARD_LAYOUT")
        Lcd.drawString("Type: ALT+a = %s (layout %s)" % ("ą" if layout == "pl" else ("ä" if layout == "de" else "a"), layout), 5, y + 15)
        if self.state == "trying":
            self._drawn = self._seconds_left()
            Lcd.setTextColor(theme["WARNING"], theme["BG"])
            Lcd.drawString("OPT = keep it (%ds)" % self._drawn, 5, 108)
            Lcd.drawString("any other key = undo", 5, 120)
        else:
            Lcd.setTextColor(theme["ERROR"] if self.message.startswith("Not") else theme["ACCENT"], theme["BG"])
            if self.message:
                Lcd.drawString(self.message[:36], 5, 108)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString("[ENTER] %s  [ESC] Back" % ("Switch off" if Lcd.font_active else "Try the font"), 5, 120)
