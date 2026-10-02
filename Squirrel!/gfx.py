# gfx.py - the display, as the rest of the app sees it
#
# Every module draws through `Lcd` from here instead of M5.Lcd.  It is the real display with two
# additions that exist for the sake of non-English text:
#
#   * a font with Polish (and other Latin) letters can be loaded: Lcd.load_font() hands a .vlw file
#     (Processing font format, made by tools/make_vlw.py) to M5.Lcd.setFont(), which the UIFlow 2
#     firmware documents as supported.  The built-in font only has ASCII;
#   * while no such font is loaded, drawString() folds the text to ASCII (ą -> a, ł -> l ...), so that
#     a Polish note shows as readable plain letters instead of garbage.  Nothing is lost: the text
#     itself is stored and edited with the real letters.
#
# All other calls go straight to M5.Lcd (the hot ones are bound once, so they cost nothing extra).

import os
from M5 import Lcd as _lcd
import charmap
from boot_log import log

_DIRECT = ("setTextColor", "setTextSize", "fillRect", "drawRect", "fillScreen", "drawLine",
           "fillCircle", "drawCircle", "drawPixel", "setBrightness", "getBrightness")


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


class Display:
    def __init__(self, lcd):
        self._lcd = lcd
        self.font_active = False
        self.font_path = None
        self.last_error = ""
        for name in _DIRECT:
            try:
                setattr(self, name, getattr(lcd, name))
            except Exception:
                pass

    def drawString(self, text, x, y, *rest):
        if not self.font_active:
            try:
                if len(text.encode()) != len(text):
                    text = charmap.fold(text)
            except Exception:
                pass
        return self._lcd.drawString(text, x, y, *rest)

    def __getattr__(self, name):                      # anything not defined above is the real display's
        return getattr(self._lcd, name)

    def find_font(self, candidates):
        for path in candidates:
            if _exists(path):
                return path
        return None

    def load_font(self, candidates):
        """Make the display draw with the .vlw font.  Returns True on success; the reason is in last_error."""
        path = self.find_font(candidates)
        if path is None:
            self.last_error = "no font file"
            return False
        try:
            self._lcd.setFont(path)
        except Exception as e:
            self.last_error = "%s: %s" % (type(e).__name__, e)
            log(f"[FONT] {path} not loaded: {self.last_error}")
            return False
        self.font_active = True
        self.font_path = path
        self.last_error = ""
        log(f"[FONT] {path} loaded")
        return True


Lcd = Display(_lcd)


def start(enabled, candidates, skip=False):
    """Called once at start-up.  `skip` (G0 held) is the way out of a font that turns out to be unusable."""
    if skip:
        log("[FONT] skipped: G0 was held at start")
        return "skipped"
    if not enabled:
        return "off"
    return "on" if Lcd.load_font(candidates) else "failed"
