# screens/routines_screen.py - Focus Tools -> Routines: recurring reminders
#
# A routine is a text (up to 50 characters), a time of day and the days of the week it applies to.  When it is due
# the scheduler shows a full-screen notification: OPT = done (counts in the statistics), DEL = skip, no reaction
# for 30 s = it comes back after ROUTINE_SNOOZE_MIN minutes (see scheduler.py).
#
# list:   UP/DOWN, ENTER opens a routine or creates a new one, ESC back
# form:   Text / Time / Days / Active / Delete - ENTER on a row edits it, ESC back to the list
# time:   LEFT/RIGHT hour or minutes, UP/DOWN change it, ENTER accept, ESC cancel
# days:   LEFT/RIGHT choose a day, ENTER tick/untick it, ESC done

from gfx import Lcd
from line_editor import LineEditor
from scheduler import DAYS, RoutineStore
from appconfig import days_shown
from screens.base_screen import BaseScreen

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

    @property
    def store(self):
        return self.app.routines

    def on_enter(self, **kwargs):
        self.mode, self.i, self.top, self._confirm = "list", 0, 0, False

    def on_exit(self):
        self.app.keypad.set_text_mode(False)

    # ---------------------------------------------------------------- rows

    def _list_rows(self):
        rows = ["+ [New Routine]"]
        for r in self.store.items:
            days = days_shown(r["d"]) if r["on"] else "off".ljust(13)
            rows.append("%02d:%02d %s %s" % (r["h"], r["m"], days, r["t"]))
        return rows

    def _form_rows(self):
        r = self.store.items[self.idx]
        return ["Text: " + r["t"], "Time: %02d:%02d" % (r["h"], r["m"]), "Days: " + days_shown(r["d"]),
                "Active: " + ("yes" if r["on"] else "no"), "Delete" + ("  (ENTER again)" if self._confirm else "")]

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
        getattr(self, "_in_" + self.mode)(action)

    def _in_list(self, action):
        rows = len(self.store.items) + 1
        if action in ('UP', 'DOWN'):
            self.i, self.top = self._step(self.i, self.top, rows, -1 if action == 'UP' else 1)
        elif action in ('ENTER', 'RIGHT'):
            if self.i == 0:
                self.store.items.append(RoutineStore.new())
                self.store.save()
                self.idx = len(self.store.items) - 1
            else:
                self.idx = self.i - 1
            self.mode, self.f, self._confirm = "form", 0, False
        elif action in ('ESC', 'LEFT'):
            self.app.set_screen("MENU", menu_name="FOCUS")

    def _in_form(self, action):
        r = self.store.items[self.idx]
        if action != 'ENTER' or self.f != 4:
            self._confirm = False
        if action in ('UP', 'DOWN'):
            self.f = (self.f + (-1 if action == 'UP' else 1)) % 5
        elif action in ('ESC', 'LEFT'):
            self.mode = "list"
            self.i = self.idx + 1
            self.top = max(0, min(self.i, len(self.store.items) + 1 - _VISIBLE))
        elif action in ('ENTER', 'RIGHT'):
            if self.f == 0:
                self.edit = LineEditor(r["t"], 50)
                self.mode = "text"
                self.app.keypad.set_text_mode(True)
            elif self.f == 1:
                self.h, self.m, self.sel, self.mode = r["h"], r["m"], 0, "time"
            elif self.f == 2:
                self.sel, self.mode = 0, "days"
            elif self.f == 3:
                r["on"] = not r["on"]
                self.store.save()
            elif self._confirm:
                del self.store.items[self.idx]
                self.store.save()
                self.mode, self.i, self.top = "list", 0, 0
            else:
                self._confirm = True

    def _in_text(self, action):
        if action == 'ENTER':
            self.store.items[self.idx]["t"] = self.edit.buf.strip() or "Routine"
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
            self.store.save()
            self.mode = "form"

    # ---------------------------------------------------------------- drawing

    def render(self, renderer):
        theme = renderer.theme
        if self.mode == "list":
            renderer.render_menu("Routines", self._list_rows(), self.i, self.top, _VISIBLE)
        elif self.mode == "form":
            renderer.render_menu("Routine", self._form_rows(), self.f, 0, _VISIBLE)
        else:
            renderer.clear()
            Lcd.setTextSize(1)
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString({"text": "Routine text", "time": "Time", "days": "Days"}[self.mode], 5, 8)
            if self.mode == "text":
                renderer.render_keypad_mode_indicator(getattr(self.app, 'keypad', None))
                Lcd.drawRect(5, 40, 230, 22, theme["ACCENT"])
                Lcd.drawString(self.edit.view(35), 10, 47)
                Lcd.drawString("%d/50" % len(self.edit.buf), 5, 70)
                Lcd.drawString("[ENTER] Save | [ESC] Cancel", 5, 115)
            elif self.mode == "time":
                for n, (text, x) in enumerate((("%02d" % self.h, 70), ("%02d" % self.m, 130))):
                    Lcd.setTextColor(theme["WARNING"] if n == self.sel else theme["FG"], theme["BG"])
                    Lcd.setTextSize(3)
                    Lcd.drawString(text, x, 45)
                Lcd.setTextSize(1)
                Lcd.setTextColor(theme["FG"], theme["BG"])
                Lcd.drawString("<> hour/min   up/down change   ENTER ok", 5, 115)
            else:
                r = self.store.items[self.idx]
                for n in range(7):
                    on = r["d"] >> n & 1
                    Lcd.setTextColor(theme["WARNING"] if n == self.sel else theme["FG"], theme["BG"])
                    Lcd.drawString(("[%s]" if on else " %s ") % DAYS[n], 20 + n * 28, 50)
                Lcd.setTextColor(theme["FG"], theme["BG"])
                Lcd.drawString("<> day   ENTER tick   ESC done", 5, 115)
