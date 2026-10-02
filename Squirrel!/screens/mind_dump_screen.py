# screens/mind_dump_screen.py - quick capture of a thought
#
# Simpler than a note: a few lines of text (MIND_DUMP_MAX_CHARS, 200), ENTER saves.  The thought goes to the
# Mind Dump list (Notes -> Mind Dump).  Editing it there turns it into a proper note: it moves to Notes
# (see NoteEditorScreen) and the user is told so.
# It opens from the clock (Aa) and from Notes -> Mind Dump -> + [New Item], and returns to where it came from.
# ESC on a screen with text asks for a second ESC, so a thought is not lost to a slip of the finger.

import time
from gfx import Lcd
from appconfig import cfg
from line_editor import LineEditor
from text_layout import layout, locate, scroll_to
from screens.base_screen import BaseScreen

_FROM_MENU = ("MENU", {"menu_name": "NOTES_ROOT"})
COLS, ROWS, ROW_H = 36, 6, 13


class MindDumpScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)
        self._return_to = _FROM_MENU
        self._armed = False
        self._top = 0
        self.edit = LineEditor("", 200)

    def on_enter(self, return_to=None, **kwargs):
        self.edit = LineEditor("", cfg.get("MIND_DUMP_MAX_CHARS"))
        self._return_to = return_to or _FROM_MENU
        self._armed = False
        self._top = 0
        self.app.keypad.set_text_mode(True)

    def on_exit(self):
        self.app.keypad.set_text_mode(False)

    def _leave(self):
        self.app.keypad.set_text_mode(False)
        name, kwargs = self._return_to
        self.app.set_screen(name, **kwargs)

    def _save(self):
        text = self.edit.buf.strip()
        if not text:
            self.app.renderer.render_alert("Write something first!")
            time.sleep(0.6)
            return
        limit = cfg.get("NOTE_TITLE_MAX_LEN")
        title = self.app.storage.unique_title("MIND", text.split("\n")[0][:limit].rstrip(), limit)
        if self.app.storage.save_item("MIND", title, text):
            self.app.renderer.render_options("Saved to Mind Dump!")
        else:
            self.app.renderer.render_alert("Save failed!")
        time.sleep(0.6)
        self._leave()

    def handle_input(self, action):
        if action == 'ESC':
            if self.edit.buf.strip() and not self._armed:
                self._armed = True
                return
            self._leave()
            return
        self._armed = False
        if action == 'ENTER':
            self._save()
        else:
            self.edit.handle(action)

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("Mind Dump", 5, 5)
        renderer.render_keypad_mode_indicator(getattr(self.app, 'keypad', None))
        Lcd.drawRect(5, 22, 230, 88, theme["ACCENT"])
        rows = layout([self.edit.buf], COLS)
        row, offset = locate(rows, 0, self.edit.cur)
        self._top = scroll_to(self._top, row, ROWS, len(rows))
        for i in range(ROWS):
            n = self._top + i
            if n >= len(rows):
                break
            Lcd.drawString(self.edit.buf[rows[n][1]:rows[n][2]], 10, 26 + i * ROW_H)
        if self._top <= row < self._top + ROWS:
            Lcd.fillRect(10 + 6 * offset, 26 + (row - self._top) * ROW_H + 10, 6, 2, theme["ACCENT"])
        counter = "%d/%d" % (len(self.edit.buf), self.edit.max_len)
        if self._armed:
            Lcd.setTextColor(theme["ERROR"], theme["BG"])
            Lcd.drawString("ESC again = discard the text", 5, 115)
        else:
            Lcd.drawString("[ENTER] Save | [ESC] Discard", 5, 115)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(counter, 235 - 6 * len(counter), 115)
