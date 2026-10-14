# screens/ble_head_screen.py - Settings -> Bluetooth on the head (the Cardputer): its devices and the sync
#
#   Sync now          every device, then a second round for those that still differ
#   Add device        look for Squirrel! devices in range (they must have Bluetooth sync open); ENTER adds one and
#                     syncs it at once - it joins (gets its slot), its own records stay its own
#   <a device>        when it was synced last and what happened; ENTER syncs only it, DEL twice forgets it
#   Be visible        this device as a node (for a phone / the Web Bluetooth page)
#   Auto sync         ENTER switches the period: off (on demand) / every 15, 30, 60, 120, 240 min (BLE_AUTO_SYNC_MIN,
#                     ble/auto.py; the devices get it with the next sync)
# While the radio works: what it is doing; ESC stops.  Opened with mode="time" (Time and date -> Time from a device):
# takes the time of the first device with a valid hardware clock, then goes back.  Opened with mode="quick" (the
# clock's Aa, the TAB menu's Quick sync): syncs every device, shows the result for a moment and goes back (`back`).
import time
from boot_log import log
from gfx import Lcd
from screens.base_screen import BaseScreen
from appconfig import cfg
from i18n import _, fill
from ble.central import STATUS_TEMPLATES, RESULT_TEMPLATES, REASON_TEMPLATES

_VISIBLE = 5
_SCAN_S = 8
_QUICK_SHOW_MS = 2500
_AUTO_STEPS = (0, 15, 30, 60, 120, 240)


def _ago(wire):
    if not wire:
        return _("never")
    from timeutil import wire_now
    s = wire_now() - wire
    if s < 120:
        return _("just now")
    if s < 7200:
        return _("%d min ago") % (s // 60)
    if s < 172800:
        return _("%d h ago") % (s // 3600)
    return _("%d days ago") % (s // 86400)


class BleHeadScreen(BaseScreen):
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self.head = None
        self.peers = None
        self.mode = "menu"              # menu / busy / found
        self.sel = self.top = 0
        self._confirm = None
        self._after = None              # what the busy radio is doing: "scan" / "sync" / "time"
        self._code = ""                 # pairing: the digits typed so far
        self._shown = None
        self._back = None               # quick sync: where to go when it is done
        self._done_at = None            # quick sync: when it ended (the result stays up for _QUICK_SHOW_MS)

    def on_enter(self, mode=None, back=None, **kwargs):
        from ble.node_data import for_app
        if getattr(self.app, "ble_auto", None) is not None:
            self.app.ble_auto.cancel()                 # one session at a time: this screen's
        from ble.central import BleHead
        data, self.peers = for_app(self.app)
        self.head = BleHead(data, self.peers, log=log)
        self.app.radio.ble_in_use = True
        self.mode, self.sel, self.top, self._confirm = "menu", 0, 0, None
        self._back, self._done_at = back, None
        if mode == "time":
            self._run("time", lambda: self.head.sync(time_only=True))
        elif mode == "quick":                       # the clock's Aa / the TAB menu: sync everything, then go back
            self._run("quick", lambda: self.head.sync())

    def on_exit(self):
        if self.head is not None:
            self.head.stop()
        self.app.radio.ble_in_use = False
        self.app.services.paused = False

    # ---------------------------------------------------------------------------------------------- rows
    def _rows(self):
        rows = [("sync", _("Sync now")), ("add", _("Add device"))]
        for n in self.peers.nodes:
            label = "%s  %s" % (n["name"].replace("Squirrel! ", ""), _ago(n.get("synced")))
            if self._confirm == n["addr"]:
                label = _("DEL again: forget %s") % n["name"].replace("Squirrel! ", "")
            rows.append(("node", label, n))
        rows.append(("visible", _("Be visible (for a phone)")))
        rows.append(("auto", _("Auto sync: %s") % _auto_label(cfg.get("BLE_AUTO_SYNC_MIN"))))
        return rows

    def _found_rows(self):
        known = {n["addr"] for n in self.peers.nodes}
        return [(addr, t, name) for addr, t, name in self.head.found if addr not in known]

    # ---------------------------------------------------------------------------------------------- input
    def _move(self, count, delta):
        self.sel = (self.sel + delta) % max(1, count)
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + _VISIBLE:
            self.top = self.sel - _VISIBLE + 1

    def _run(self, what, start):
        self._after = what
        self.mode = "busy"
        try:
            start()
        except Exception as e:
            log(f"[BLE] head: {type(e).__name__}: {e}")
            self.head.status = _("Bluetooth failed: %s") % e
            self.head.stop()

    def handle_input(self, action):
        if self.mode == "busy":
            if self.head.need_code and isinstance(action, str) and len(action) == 1 and action.isdigit():
                self._code = (self._code + action)[:6]
                return
            if self.head.need_code and action in ('BACKSPACE', 'DEL'):
                self._code = self._code[:-1]
                return
            if self.head.need_code and action == 'ENTER' and len(self._code) == 6:
                self.head.enter_code(self._code)
                self._code = ""
                return
            if action in ('ESC', 'LEFT'):
                self.head.stop()
                self.head.status = _("Stopped")
            elif action == 'ENTER' and not self.head.busy:
                self._done_busy()
            return
        if self.mode == "found":
            found = self._found_rows()
            if action in ('UP', 'DOWN'):
                self._move(len(found), -1 if action == 'UP' else 1)
            elif action in ('ESC', 'LEFT'):
                self.mode, self.sel, self.top = "menu", 0, 0
            elif action in ('ENTER', 'RIGHT') and found:
                addr, addr_type, name = found[self.sel]
                try:
                    self.peers.add(addr, addr_type, name)
                except ValueError as e:
                    self.head.status = str(e)
                    self.mode = "busy"
                    return
                self._run("sync", lambda: self.head.sync(only=addr))
            return
        rows = self._rows()
        if action != 'DEL':
            self._confirm = None
        if action in ('UP', 'DOWN'):
            self._move(len(rows), -1 if action == 'UP' else 1)
        elif action in ('ESC', 'LEFT'):
            self.app.set_screen("MENU", menu_name="SETTINGS")
        elif action == 'DEL' and rows[self.sel][0] == "node":
            node = rows[self.sel][2]
            if self._confirm == node["addr"]:
                self.peers.remove(node["addr"])
                if self.head.data.auth is not None:
                    self.head.data.auth.forget(node["addr"])       # added again: paired again, with a new code
                self._confirm = None
                self.sel = min(self.sel, len(self._rows()) - 1)
            else:
                self._confirm = node["addr"]
        elif action in ('ENTER', 'RIGHT'):
            kind = rows[self.sel][0]
            if kind == "sync":
                self._run("sync", lambda: self.head.sync())
            elif kind == "add":
                self._run("scan", lambda: self.head.scan(_SCAN_S))
            elif kind == "node":
                addr = rows[self.sel][2]["addr"]
                self._run("sync", lambda: self.head.sync(only=addr))
            elif kind == "auto":
                now = cfg.get("BLE_AUTO_SYNC_MIN")
                later = [m for m in _AUTO_STEPS if m > now]
                cfg.set("BLE_AUTO_SYNC_MIN", later[0] if later else 0)       # saved to config.txt
            elif kind == "visible":
                self.head.stop()
                self.app.set_screen("BLE_SYNC", back=("BLE_HUB", {}))

    def _done_busy(self):
        if self._after == "quick":
            back = self._back or ("CLOCK", {})
            self.app.set_screen(back[0], **back[1])
            return
        if self._after == "time":
            self.app.set_screen("MENU", menu_name="TIME_DATE")
            return
        self.mode, self.sel, self.top = ("found" if self._after == "scan" else "menu"), 0, 0

    def needs_refresh(self):
        if self.head is None:
            return False
        self.head.tick()
        self.app.services.paused = self.head.state == "syncing"     # see services.py
        if self.mode == "busy" and not self.head.busy and self._after == "scan":
            self._done_busy()                              # straight to the list of what was found
        elif self.mode == "busy" and not self.head.busy and self._after == "quick" and not self.head.need_code:
            now = time.ticks_ms()
            if self._done_at is None:
                self._done_at = now
            elif time.ticks_diff(now, self._done_at) >= _QUICK_SHOW_MS:
                self._done_busy()                          # the result was up long enough: back to the clock
                return True
        shown = (self.mode, self.head.state, self.head.status, self.sel, self._confirm, self.head.need_code, self._code)
        if shown != self._shown:
            self._shown = shown
            return True
        return False

    # ---------------------------------------------------------------------------------------------- drawing
    def render(self, renderer):
        theme = renderer.theme
        if self.mode == "menu":
            rows = self._rows()
            renderer.render_menu(_("Bluetooth"), [r[1] for r in rows], self.sel, self.top, _VISIBLE)
            if rows[self.sel][0] == "node":
                result = self.head.results.get(rows[self.sel][2]["addr"])
                if result:
                    Lcd.setTextColor(theme["ACCENT"], theme["BG"])
                    Lcd.drawString(_result_text(result)[:38], 5, 124)
            return
        if self.mode == "found":
            found = self._found_rows()
            rows = ["%s  %s" % (name.replace("Squirrel! ", ""), addr[-4:]) for addr, _t, name in found]
            renderer.render_menu(_("Add device"), rows or [_("(none: open Bluetooth sync there)")], self.sel, self.top, _VISIBLE)
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            Lcd.drawString(_("ENTER add + sync   ESC back"), 5, 124)
            return
        renderer.clear()
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(_("# Bluetooth"), 5, 5)
        Lcd.drawString(fill(self.head.status, STATUS_TEMPLATES, REASON_TEMPLATES)[:38], 10, 30)
        if self.head.need_code:
            Lcd.setTextSize(3)
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            Lcd.drawString((self._code + "______")[:6], 66, 56)
            Lcd.setTextSize(1)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString(_("digits, then ENTER   [ESC] Stop"), 5, 115)
            return
        y = 50
        for n in self.peers.nodes:
            result = self.head.results.get(n["addr"])
            if result and y < 100:
                Lcd.drawString(("%s: %s" % (n["name"].replace("Squirrel! ", ""), _result_text(result)))[:38], 10, y)
                y += 14
        Lcd.drawString(_("[ESC] Stop") if self.head.busy else _("[ENTER] OK"), 5, 115)


def _auto_label(minutes):
    if not minutes:
        return _("on demand")
    return _("every %d min") % minutes if minutes < 60 or minutes % 60 else _("every %d h") % (minutes // 60)


def _result_text(result):
    """A node's result ("routines 2/0, 1 settings") in the current language, part by part."""
    return ", ".join(fill(part, RESULT_TEMPLATES, REASON_TEMPLATES) for part in result.split(", "))
