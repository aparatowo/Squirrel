# screens/ble_sync_screen.py - Settings -> Bluetooth sync: this device waits for the head (docs/implementation/en/bluetooth.md 4)
#
# Opening the screen switches the radio on and advertises the Squirrel! service for WINDOW_S; the head (or a phone with
# nRF Connect / the Web Bluetooth page) connects and syncs; when it disconnects - or nobody came - the radio goes off.
# ESC / LEFT / a tap on the title stops at once.  The screen stays on meanwhile (no dimming, no sleep).
# Opened with quick=True (the watch's clock: swipe down) it goes back by itself once the session is over.
import time
from boot_log import log
from gfx import Lcd
from screens.base_screen import BaseScreen
from ui.touch import has_touch, TouchList
from i18n import _

WINDOW_S = 120
_QUICK_SHOW_MS = 2500        # quick: how long the result stays up before going back


class BleSyncScreen(BaseScreen):
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self.node = None
        self._touch = has_touch()
        self._list = TouchList() if self._touch else None
        self._shown = None
        self._result = None
        self._quick = False
        self._done_at = None

    @property
    def full_height(self):
        return self._touch

    def on_enter(self, back=None, quick=False, **kwargs):
        from ble.node_data import for_app, device_name
        from ble.peripheral import BleNode
        if getattr(self.app, "ble_auto", None) is not None:
            self.app.ble_auto.cancel()                 # one session at a time: this screen's
        self._back_to = back or ("MENU", {"menu_name": "SETTINGS"})
        data, _peers = for_app(self.app)
        self.node = BleNode(data, name=device_name(), log=log)
        self._result = None
        self._quick, self._done_at = quick, None
        self.app.radio.ble_in_use = True
        try:
            self.node.start(WINDOW_S)
        except Exception as e:
            log(f"[BLE] cannot start: {type(e).__name__}: {e}")
            self._result = _("Bluetooth failed: %s") % e
            self.node.stop()

    def on_exit(self):
        if self.node is not None:
            self.node.stop()
            self.node = None
        self.app.radio.ble_in_use = False
        self.app.services.paused = False

    def _back(self):
        self.app.set_screen(self._back_to[0], **self._back_to[1])

    def handle_input(self, action):
        if action in ('ESC', 'LEFT'):
            self._back()
        elif self._touch and action in ('ENTER', 'OPT'):
            if self._list.hit(getattr(self.app.keypad, "tap_xy", None), 0, 0) == "back":
                self._back()

    def needs_refresh(self):
        node = self.node
        if node is None:
            return False
        changed = node.tick()
        self.app.services.paused = node.state == "connected"        # see services.py
        if changed and node.state == "off" and self._result is None:
            c = node.counts
            if c["list"] or c["get"] or c["put"] or c["delete"]:
                self._result = _("Done: %d received, %d sent") % (c["put"] + c["delete"], c["get"] + c["list"])
            else:
                self._result = _("Connected, nothing asked") if node.was_connected else _("Nobody came")
        if self._quick and node.state == "off":
            now = time.ticks_ms()
            if self._done_at is None:
                self._done_at = now
            elif time.ticks_diff(now, self._done_at) >= _QUICK_SHOW_MS:
                self._back()
                return True
        shown = (node.state, node.seconds_left(), node.counts["put"], node.counts["get"], self._result, node.passkey)
        if shown != self._shown:
            self._shown = shown
            return True
        return False

    def _lines(self):
        node = self.node
        if node is None or node.state == "off":
            lines = [self._result or _("Off")]
            if node is not None and node.last_error:
                lines.append(_("Last error: %s") % node.last_error[:30])
            return lines
        if node.passkey:
            return [_("Pairing code:"), node.passkey[:3] + " " + node.passkey[3:], _("type it on the squirrel")]
        if node.state == "advertising":
            left = node.seconds_left() or 0
            return [_("Waiting for the squirrel"), _("%d:%02d left") % (left // 60, left % 60)]
        c = node.counts
        return [_("Connected"), _("received %d  sent %d") % (c["put"] + c["delete"], c["get"] + c["list"])]

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        lines = self._lines()
        if self._touch:
            self._list.draw_header(theme, _("Bluetooth sync"))
            from text_layout import wrap_line
            Lcd.setTextSize(2)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            cols = (Lcd.screen_size()[0] - 16) // 12
            y = self._list.HEADER + 20
            for line in lines:
                for a, b in wrap_line(line, cols):
                    Lcd.drawString(line[a:b].strip(), 8, y)
                    y += 24
                y += 8
            return
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(_("# Bluetooth sync"), 5, 5)
        y = 40
        for line in lines:
            Lcd.drawString(line[:38], 10, y)
            y += 16
        Lcd.drawString(_("[ESC] Stop"), 5, 115)
