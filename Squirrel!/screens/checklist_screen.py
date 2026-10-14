# screens/checklist_screen.py - a To-Do with ">" items, ticked one by one: a shopping list, the steps of a task ...
#
# Opened from the To-Do list instead of the viewer when the To-Do has lines that start with ">" (todo_editor.py).
#   with a keyboard (the Cardputer):  UP / DOWN item, OPT tick / un-tick, ENTER edit the list, ESC back
#   with a touch screen (the watch):  a tap on an item ticks / un-ticks it, a tap on the title (or a swipe right) back
# Ticking the last item ticks the whole To-Do; the text of the file is never changed by ticking.
from gfx import Lcd
from features import has
from screens.base_screen import BaseScreen
from ui.touch import has_touch, TouchList
from i18n import _

_VISIBLE = 5


class ChecklistScreen(BaseScreen):
    modifiers_as_keys = True            # OPT is the tick key

    def __init__(self, app):
        super().__init__(app)
        self._touch = has_touch()
        self._list = TouchList() if self._touch else None
        self.visible = self._list.visible if self._touch else _VISIBLE
        self.title = ""
        self.index = 0                  # the To-Do's file
        self.items = []                 # [(text, ticked)]
        self.sel = 0
        self.top = 0

    @property
    def full_height(self):
        return self._touch

    def on_enter(self, file_index=0, title="", **kwargs):
        self.index, self.title = file_index, title
        self.sel = self.top = 0
        self._reload()

    def _reload(self):
        self.items = self.app.todo_editor.checklist_state(self.index)
        self.sel = min(self.sel, max(0, len(self.items) - 1))

    def _back(self):
        self.app.set_screen("MENU", menu_name="TODO")

    def _move(self, delta):
        n = len(self.items)
        if not n:
            return
        self.sel = (self.sel + delta) % n
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + self.visible:
            self.top = self.sel - self.visible + 1

    def _toggle(self):
        if not self.items:
            return
        from scheduler import valid_now, day_key
        t = valid_now()
        if t is None:
            self.app.renderer.render_alert(_("Set time first!"))        # a done date needs a real clock
            import time
            time.sleep(0.8)
            return
        self.app.todo_editor.toggle_item(self.index, self.items[self.sel][0], day_key(t))
        self._reload()

    def handle_input(self, action):
        if action in ('ESC', 'LEFT'):
            self._back()
        elif action in ('UP', 'DOWN'):
            self._move(-1 if action == 'UP' else 1)
        elif self._touch and action in ('ENTER', 'OPT'):
            hit = self._list.hit(getattr(self.app.keypad, "tap_xy", None), self.top, len(self.items))
            if hit == "back":
                self._back()
            elif hit is not None:
                self.sel = hit
                self._toggle()
        elif action == 'OPT':
            self._toggle()
        elif action == 'ENTER' and has("text_edit"):
            content = self.app.storage.read_item("TODO", self.index) or ""
            self.app.set_screen("NOTE_EDITOR", title=self.title, body=content, file_index=self.index, menu_name="TODO")

    def _rows(self):
        return [("[X] " if ticked else "[ ] ") + text for text, ticked in self.items]

    def render(self, renderer):
        ticked = sum(1 for _t, d in self.items if d)
        count = "%d/%d" % (ticked, len(self.items))
        rows = self._rows() or ["(no items: lines starting with >)"]
        if self._touch:
            renderer.clear()
            theme = renderer.theme
            self._list.draw_header(theme, self.title, count)
            for row in range(self.visible):
                i = self.top + row
                if i >= len(rows):
                    break
                self._list.draw_row(theme, row, rows[i], i == self.sel and bool(self.items))
            return
        renderer.render_menu("%s %s" % (self.title[:26], count), rows, self.sel, self.top, self.visible)
        Lcd.setTextColor(renderer.theme["ACCENT"], renderer.theme["BG"])
        Lcd.drawString(_("OPT = done   ENTER = edit") if has(_("text_edit")) else _("OPT = done"), 5, 124)
