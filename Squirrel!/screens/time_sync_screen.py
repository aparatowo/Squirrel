# screens/time_sync_screen.py - set the clock over Wi-Fi (opened from Settings)
#
# Starts a sync as soon as it opens; the service does the work in the background, so
# this screen only shows progress.  Leaving it does not interrupt a running sync.
#   ENTER - try again        ESC - back to Settings

from gfx import Lcd
from screens.base_screen import BaseScreen


class TimeSyncScreen(BaseScreen):
    keeps_screen_on = True         # the screen must not dim while this one is shown
    def __init__(self, app):
        super().__init__(app)
        self._drawn = None

    def on_enter(self, **kwargs):
        self._drawn = None
        if not self.app.timesync.busy:
            self.app.timesync.start("manual")

    def _snapshot(self):
        svc = self.app.timesync
        return (svc.state, svc.message, svc.elapsed_s())

    def needs_refresh(self):
        return self._snapshot() != self._drawn

    def handle_input(self, action):
        if action == 'ESC':
            self.app.set_screen("MENU", menu_name="TIME_DATE")
        elif action == 'ENTER' and not self.app.timesync.busy:
            self.app.timesync.start("manual")

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        svc = self.app.timesync
        self._drawn = self._snapshot()

        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("# Time via WiFi", 5, 5)
        if svc.ssid:
            Lcd.drawString("Network: " + svc.ssid[:22], 5, 24)

        if svc.state == "done":
            colour = theme["ACCENT"]
        elif svc.state == "failed":
            colour = theme["ERROR"]
        else:
            colour = theme["WARNING"]
        Lcd.setTextColor(colour, theme["BG"])
        text = svc.message or "Ready"
        if svc.busy:
            text += " %ds" % svc.elapsed_s()
        Lcd.drawString(text[:38], 5, 44)
        if len(text) > 38:
            Lcd.drawString(text[38:76], 5, 56)

        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("Phone hotspot must be ON", 5, 82)
        Lcd.drawString("(2.4 GHz). WiFi and BT are", 5, 94)
        Lcd.drawString("switched off afterwards.", 5, 106)
        Lcd.drawString("[ENTER] Retry  [ESC] Back", 5, 124)
