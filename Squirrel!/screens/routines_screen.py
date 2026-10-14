# screens/routines_screen.py - Focus tools -> Routines: recurring reminders
#
# A routine is a text (up to 50 characters), a time of day and the days of the week it applies to.  When it is due
# the scheduler shows a full-screen notification: OPT = done (counts in the statistics), DEL = skip, no reaction
# for 30 s = it comes back after ROUTINE_SNOOZE_MIN minutes (see scheduler.py).
#
# list:   UP/DOWN, ENTER opens a routine or creates a new one, ESC back
# form:   Text / Time / Days / Active / Delete - ENTER on a row edits it, ESC back to the list
# time:   LEFT/RIGHT hour or minutes, UP/DOWN change it, ENTER accept, ESC cancel
# days:   LEFT/RIGHT choose a day, ENTER tick/untick it, ESC done
# devices (only with synced devices, docs/implementation/en/bluetooth.md 5): UP/DOWN a device, ENTER tick/untick, ESC done - the routine
#          comes up only on the ticked ones; all ticked = every device, the ones added later too
# On a touch screen without a keyboard (the watch) routines are only switched on / off (they are written on the
# Cardputer and come over the sync): a list on the whole panel, a tap on a routine switches it, a tap on the title
# (or a swipe right) goes back.

from gfx import Lcd
from line_editor import LineEditor
from scheduler import RoutineStore
from appconfig import days_shown, day_short
from screens.base_screen import BaseScreen
from ui.touch import has_touch, TouchList
from features import has
from i18n import _
from charmap import pad

_VISIBLE = 5


class RoutinesScreen(BaseScreen):
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self.mode = "list"
        self.i = 0                 # highlighted row of the list
        self.top = 0
        self.f = 0                 # highlighted row of the form
        self.idx = 0               # the routine being edited
        self.edit = None
        self.sel = 0               # time: 0 = hour, 1 = minutes; days: the day under the cursor
        self.h = self.m = 0
        self._confirm = False
        self._devices = []         # [(slot, name)] with synced devices (on_enter)
        self._touch = has_touch() and not has("text_edit")
        self._list = TouchList() if self._touch else None

    @property
    def full_height(self):
        return self._touch

    @property
    def store(self):
        return self.app.routines

    def on_enter(self, **kwargs):
        self.mode, self.i, self.top, self._confirm = "list", 0, 0, False
        self._devices = self._known_devices()

    @staticmethod
    def _known_devices():
        """[(slot, name)]: this device and the ones it syncs - [] when there are none (the field is not shown)."""
        try:
            import nuts
            from ble.peers import Peers
            peers = Peers(nuts.BASE_DIR + "/ble.json", nuts.BASE_DIR + "/focus/peers")
        except Exception:
            return []
        if not peers.nodes:
            return []
        return [(peers.slot, _("This device"))] + [(n["slot"], n["name"].replace("Squirrel! ", "")) for n in peers.nodes]

    def _kinds(self):
        return ["text", "time", "days"] + (["devices"] if self._devices else []) + ["active", "delete"]

    def _devices_text(self, mask):
        if mask & 255 == 255:
            return "all"
        names = [name for slot, name in self._devices if mask >> slot & 1]
        return ", ".join(names) if names else "none"

    def on_exit(self):
        self.app.keypad.set_text_mode(False)

    # ---------------------------------------------------------------- rows

    def _list_rows(self):
        rows = [_("+ [New routine]")]
        for r in self.store.items:
            days = days_shown(r["d"]).replace(" ", "") if r["on"] else pad(_("off"), 7)   # compact: room for the text
            rows.append("%02d:%02d %s %s" % (r["h"], r["m"], days, r["t"]))
        return rows

    def _form_rows(self):
        r = self.store.items[self.idx]
        text = {"text": _("Text: ") + r["t"], "time": _("Time: %02d:%02d") % (r["h"], r["m"]),
                "days": _("Days: ") + days_shown(r["d"]), "devices": _("Devices: ") + self._devices_text(r.get("to", 255)),
                "active": _("Active: ") + (_("yes") if r["on"] else _("no")),
                "delete": _("Delete") + (_("  (ENTER again)") if self._confirm else "")}
        return [text[k] for k in self._kinds()]

    @staticmethod
    def _step(index, top, count, delta):
        index = (index + delta) % count
        if index < top:
            top = index
        elif index >= top + _VISIBLE:
            top = index - _VISIBLE + 1
        return index, max(0, min(top, max(0, count - _VISIBLE)))

    # ---------------------------------------------------------------- input

    def handle_input(self, action):
        if self._touch:
            return self._in_touch(action)
        getattr(self, "_in_" + self.mode)(action)

    def _in_touch(self, action):
        items = self.store.items
        if action in ('ESC', 'LEFT'):
            self.app.set_screen("MENU", menu_name="FOCUS")
        elif action in ('UP', 'DOWN'):
            self.i, self.top = self._list.move(self.i, self.top, len(items), -1 if action == 'UP' else 1)
        elif action in ('ENTER', 'OPT'):
            hit = self._list.hit(getattr(self.app.keypad, "tap_xy", None), self.top, len(items))
            if hit == "back":
                self.app.set_screen("MENU", menu_name="FOCUS")
            elif hit is not None:
                self.i = hit
                r = items[hit]
                r["on"] = not r["on"]
                RoutineStore.state_changed(r)
                self.store.save()

    def _in_list(self, action):
        rows = len(self.store.items) + 1
        if action in ('UP', 'DOWN'):
            self.i, self.top = self._step(self.i, self.top, rows, -1 if action == 'UP' else 1)
        elif action in ('ENTER', 'RIGHT'):
            if self.i == 0:
                self.store.create()
                self.store.save()
                self.idx = len(self.store.items) - 1
            else:
                self.idx = self.i - 1
            self.mode, self.f, self._confirm = "form", 0, False
        elif action in ('ESC', 'LEFT'):
            self.app.set_screen("MENU", menu_name="FOCUS")

    def _in_form(self, action):
        r = self.store.items[self.idx]
        kinds = self._kinds()
        kind = kinds[self.f]
        if action != 'ENTER' or kind != "delete":
            self._confirm = False
        if action in ('UP', 'DOWN'):
            self.f = (self.f + (-1 if action == 'UP' else 1)) % len(kinds)
        elif action in ('ESC', 'LEFT'):
            self.mode = "list"
            self.i = self.idx + 1
            self.top = max(0, min(self.i, len(self.store.items) + 1 - _VISIBLE))
        elif action in ('ENTER', 'RIGHT'):
            if kind == "text":
                self.edit = LineEditor(r["t"], 50)
                self.mode = "text"
                self.app.keypad.set_text_mode(True)
            elif kind == "time":
                self.h, self.m, self.sel, self.mode = r["h"], r["m"], 0, "time"
            elif kind == "days":
                self.sel, self.mode = 0, "days"
            elif kind == "devices":
                self.sel, self.mode = 0, "devices"
            elif kind == "active":
                r["on"] = not r["on"]
                RoutineStore.state_changed(r)
                self.store.save()
            elif self._confirm:
                del self.store.items[self.idx]
                self.store.save()
                self.mode, self.i, self.top = "list", 0, 0
            else:
                self._confirm = True

    def _in_text(self, action):
        if action == 'ENTER':
            r = self.store.items[self.idx]
            r["t"] = self.edit.buf.strip() or _("Routine")
            RoutineStore.edited(r)
            self.store.save()
            self._end_text()
        elif action == 'ESC':
            self._end_text()
        else:
            self.edit.handle(action)

    def _end_text(self):
        self.app.keypad.set_text_mode(False)
        self.mode = "form"

    def _in_time(self, action):
        if action in ('LEFT', 'RIGHT'):
            self.sel = 1 - self.sel
        elif action in ('UP', 'DOWN'):
            d = 1 if action == 'UP' else -1
            if self.sel == 0:
                self.h = (self.h + d) % 24
            else:
                self.m = (self.m + d) % 60
        elif action == 'ENTER':
            r = self.store.items[self.idx]
            r["h"], r["m"] = self.h, self.m
            RoutineStore.edited(r)
            self.store.save()
            self.mode = "form"
        elif action == 'ESC':
            self.mode = "form"

    def _in_days(self, action):
        r = self.store.items[self.idx]
        if action == 'LEFT':
            self.sel = (self.sel - 1) % 7
        elif action == 'RIGHT':
            self.sel = (self.sel + 1) % 7
        elif action in ('ENTER', 'SPACE'):
            r["d"] ^= 1 << self.sel
        elif action == 'ESC':
            if r["d"] == 0:
                r["d"] = 127                 # no day at all would be a routine that never comes
            RoutineStore.edited(r)
            self.store.save()
            self.mode = "form"

    def _in_devices(self, action):
        r = self.store.items[self.idx]
        n = len(self._devices)
        if action in ('UP', 'DOWN'):
            self.sel = (self.sel + (-1 if action == 'UP' else 1)) % n
        elif action in ('ENTER', 'SPACE', 'RIGHT'):
            mask = r.get("to", 255)
            if mask & 255 == 255:
                mask = 0
                for slot, _name in self._devices:
                    mask |= 1 << slot
            mask ^= 1 << self._devices[self.sel][0]
            every = 0
            for slot, _name in self._devices:
                every |= 1 << slot
            r["to"] = 255 if mask & every == every else mask       # all ticked: every device, new ones too
        elif action in ('ESC', 'LEFT'):
            if not r.get("to", 255) & 255:
                r["to"] = 255                # on no device at all it would never come up
            RoutineStore.edited(r)
            self.store.save()
            self.mode = "form"

    # ---------------------------------------------------------------- drawing

    def render(self, renderer):
        theme = renderer.theme
        if self._touch:
            return self._render_touch(renderer)
        if self.mode == "list":
            renderer.render_menu(_("Routines"), self._list_rows(), self.i, self.top, _VISIBLE)
        elif self.mode == "form":
            rows = self._form_rows()
            renderer.render_menu(_("Routine"), rows, self.f, max(0, self.f - _VISIBLE + 1), _VISIBLE)
        elif self.mode == "devices":
            mask = self.store.items[self.idx].get("to", 255)
            rows = [("[X] " if mask & 255 == 255 or mask >> slot & 1 else "[ ] ") + name for slot, name in self._devices]
            renderer.render_menu(_("Devices"), rows, self.sel, 0, _VISIBLE)
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            Lcd.drawString(_("ENTER tick   ESC done"), 5, 124)
        else:
            renderer.clear()
            Lcd.setTextSize(1)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString({"text": _("Routine text"), "time": _("Time"), "days": _("Days")}[self.mode], 5, 8)
            if self.mode == "text":
                renderer.render_keypad_mode_indicator(getattr(self.app, 'keypad', None))
                Lcd.drawRect(5, 40, 230, 22, theme["ACCENT"])
                Lcd.drawString(self.edit.view(35), 10, 47)
                Lcd.drawString("%d/50" % len(self.edit.buf), 5, 70)
                Lcd.drawString(_("[ENTER] Save | [ESC] Cancel"), 5, 115)
            elif self.mode == "time":
                for n, (text, x) in enumerate((("%02d" % self.h, 70), ("%02d" % self.m, 130))):
                    Lcd.setTextColor(theme["WARNING"] if n == self.sel else theme["FG"], theme["BG"])
                    Lcd.setTextSize(3)
                    Lcd.drawString(text, x, 45)
                Lcd.setTextSize(1)
                Lcd.setTextColor(theme["FG"], theme["BG"])
                Lcd.drawString(_("<> hour/min   up/down change   ENTER ok"), 5, 115)
            else:
                r = self.store.items[self.idx]
                for n in range(7):
                    on = r["d"] >> n & 1
                    Lcd.setTextColor(theme["WARNING"] if n == self.sel else theme["FG"], theme["BG"])
                    Lcd.drawString(("[%s]" if on else " %s ") % day_short(n), 20 + n * 28, 50)
                Lcd.setTextColor(theme["FG"], theme["BG"])
                Lcd.drawString(_("<> day   ENTER tick   ESC done"), 5, 115)

    def _render_touch(self, renderer):
        theme = renderer.theme
        renderer.clear()
        items = self.store.items
        lst = self._list
        lst.draw_header(theme, _("Routines"), "%d/%d" % (self.i + 1, len(items)) if len(items) > lst.visible else None)
        if not items:
            lst.draw_row(theme, 0, _("(none yet)"), False, sub=_("add them on the squirrel"))
            return
        for row in range(lst.visible):
            n = self.top + row
            if n >= len(items):
                break
            r = items[n]
            days = days_shown(r["d"]).replace(" ", "")
            lst.draw_row(theme, row, "%02d:%02d %s" % (r["h"], r["m"], r["t"]), n == self.i,
                         sub=(_("on") if r["on"] else _("off")) + " " + days, sub_color="ACCENT" if r["on"] else "ERROR")
