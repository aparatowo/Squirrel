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
# All other calls go straight to the real display (the hot ones are bound once, so they cost nothing extra).
#
# The real display is the port's (port_config.DISPLAY_DRIVER: drivers/<driver>.py gives `lcd`; on the Cardputer M5.Lcd).
# Every display driver offers the M5.Lcd calls the app uses.  SCREEN_W / SCREEN_H: its size in pixels.

import os
import charmap
from boot_log import log
import port_config as _pc
from port_config import DISPLAY_DRIVER, DISPLAY_WIDTH as SCREEN_W
SCREEN_H = getattr(_pc, "DISPLAY_LAYOUT_HEIGHT", _pc.DISPLAY_HEIGHT)    # the height the screens are laid out for
PANEL_H = _pc.DISPLAY_HEIGHT                                            # the whole panel (a full-height screen gets it)

_lcd = __import__("drivers." + DISPLAY_DRIVER, None, None, ("lcd",)).lcd

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
        # A display drawn through a frame buffer (drivers/st7789_fb.py) shows what was drawn only on flush(); it says so
        # with _needs_flush.  M5.Lcd draws straight onto the panel: flush() does nothing there.
        self._flush = lcd.flush if getattr(lcd, "_needs_flush", False) else None
        self.font_active = False
        self.font_path = None
        self.last_error = ""
        for name in _DIRECT:
            try:
                setattr(self, name, getattr(lcd, name))
            except Exception:
                pass

    def flush(self):
        """Send what was drawn since the last flush to the panel (a frame-buffer display); call after a screen is drawn."""
        if self._flush is not None:
            self._flush()

    def full_height(self, on):
        """A screen made for the whole panel (full_height = True, e.g. touch screens) gets all of it; the others the
        layout area (SCREEN_H, centred).  Only a display that can (drivers/st7789_fb.py); elsewhere nothing changes."""
        if getattr(self._lcd, "_can_layout", False):
            self._lcd.set_layout(PANEL_H if on else SCREEN_H)

    def screen_size(self):
        """(width, height) the current screen draws in."""
        if getattr(self._lcd, "_can_layout", False):
            return SCREEN_W, self._lcd.height()
        return SCREEN_W, SCREEN_H

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
