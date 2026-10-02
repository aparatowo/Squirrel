# screens/note_editor_screen.py
import time
from gfx import Lcd
from appconfig import cfg
from screens.base_screen import BaseScreen
from text_layout import layout, locate, move_vertical, scroll_to

COLS = 36        # characters per screen row: 36 * 6 px fills the box (the old 22-26 left a quarter of the screen empty)
ROWS = 6         # screen rows shown at once
ROW_H = 13       # pixels between rows (the font is 8-13 px high)
TEXT_X, TEXT_Y = 10, 26


class NoteEditorScreen(BaseScreen):
    """Multi-line text editor for notes and TODOs - used for a NEW item as well as for editing one.

    Long lines wrap at spaces; the cursor moves by screen rows.  The first line is the title (its first
    NOTE_TITLE_MAX_LEN / TODO_TITLE_MAX_LEN characters, or all of it if it is shorter); a later line never
    becomes part of the title.  The text is limited to NOTE_BODY_MAX_CHARS / TODO_MAX_CHARS characters.

    Keys (FN layer for the arrows):
        FN+UP / DOWN / LEFT / RIGHT   cursor, UP / DOWN by screen rows
        Backspace / FN+Backspace      delete before / after the cursor (joins lines)
        ENTER                         new line
        CTRL+S                        save and return
        ESC                           discard and return
    """

    def __init__(self, app):
        super().__init__(app)
        self.body_lines = [""]
        self.cursor_line = 0
        self.cursor_col = 0
        self.scroll_top = 0              # first visible SCREEN row
        self.max_visible_lines = ROWS
        self.menu_name = "NOTES"
        self.file_index = None           # None = a new item, an int = the file being edited
        self.max_chars = 1000
        self.title_max = 20
        self._want = None                # column to aim for while moving up and down

    # ------------------------------------------------------------------ lifecycle

    def on_enter(self, title="", body="", file_index=None, menu_name="NOTES", **kwargs):
        self.menu_name = menu_name
        self.file_index = file_index
        todo = menu_name == "TODO"
        self.max_chars = cfg.get("TODO_MAX_CHARS" if todo else "NOTE_BODY_MAX_CHARS")
        self.title_max = cfg.get("TODO_TITLE_MAX_LEN" if todo else "NOTE_TITLE_MAX_LEN")

        # An existing item arrives complete (its first line is the title); a new one is empty.
        if body:
            self.body_lines = body.split("\n")
        elif title:
            self.body_lines = [title]
        else:
            self.body_lines = [""]

        self.cursor_line = len(self.body_lines) - 1
        self.cursor_col = len(self.body_lines[self.cursor_line])
        self.scroll_top = 0
        self._want = None
        self._scroll(layout(self.body_lines, COLS))

        if hasattr(self.app, 'keypad'):
            self.app.keypad.set_text_mode(True)

    def on_exit(self):
        if hasattr(self.app, 'keypad'):
            self.app.keypad.set_text_mode(False)

    # ------------------------------------------------------------------ helpers

    def _current_line(self):
        return self.body_lines[self.cursor_line]

    def _total_chars(self):
        return sum(len(line) for line in self.body_lines) + len(self.body_lines) - 1

    def _scroll(self, rows):
        row, _off = locate(rows, self.cursor_line, self.cursor_col)
        self.scroll_top = scroll_to(self.scroll_top, row, ROWS, len(rows))

    def _title(self):
        """The first non-empty line, at most title_max characters of it."""
        for line in self.body_lines:
            stripped = line.strip()
            if stripped:
                return stripped[:self.title_max].rstrip()
        return ""

    def _save(self):
        """Persist the buffer and navigate back."""
        full_body = "\n".join(self.body_lines)
        title = self._title()
        if not title:
            self.app.renderer.render_alert("Title Required!")
            time.sleep(0.6)
            return

        if self.menu_name == "MIND":
            # a Mind Dump thought that is edited has grown into a note: it moves to Notes
            self.app.note_editor.create_note(title, full_body)
            if self.file_index is not None:
                self.app.storage.delete_item("MIND", self.file_index)
            if hasattr(self.app, 'keypad'):
                self.app.keypad.set_text_mode(False)
            self.app.renderer.render_options("Moved to Notes!")
            time.sleep(1.0)
            self.app.set_screen("MENU", menu_name="MIND")
            return

        if self.file_index is None:
            if self.menu_name == "TODO":
                self.app.todo_editor.create_todo(full_body)
            else:
                self.app.note_editor.create_note(title, full_body)
        else:
            self.app.storage.update_item(self.menu_name, self.file_index, title, full_body)

        if hasattr(self.app, 'keypad'):
            self.app.keypad.set_text_mode(False)

        self.app.renderer.render_options("Saved!")
        time.sleep(0.6)
        self.app.set_screen("MENU", menu_name=self.menu_name)

    # ------------------------------------------------------------------ input

    def handle_input(self, action):
        if action in ('CTRL+s', 'CTRL+S'):
            self._save()
            return

        if action == 'ESC':
            if hasattr(self.app, 'keypad'):
                self.app.keypad.set_text_mode(False)
            self.app.set_screen("MENU", menu_name=self.menu_name)
            return

        rows = layout(self.body_lines, COLS)
        cur = self._current_line()
        vertical = False

        if action in ('UP', 'DOWN'):
            if self._want is None:
                self._want = locate(rows, self.cursor_line, self.cursor_col)[1]
            self.cursor_line, self.cursor_col = move_vertical(
                rows, self.cursor_line, self.cursor_col, -1 if action == 'UP' else 1, self._want)
            vertical = True

        elif action == 'LEFT':
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = len(self._current_line())

        elif action == 'RIGHT':
            if self.cursor_col < len(cur):
                self.cursor_col += 1
            elif self.cursor_line < len(self.body_lines) - 1:
                self.cursor_line += 1
                self.cursor_col = 0

        elif action == 'ENTER':
            if self._total_chars() < self.max_chars:
                self.body_lines[self.cursor_line] = cur[:self.cursor_col]
                self.body_lines.insert(self.cursor_line + 1, cur[self.cursor_col:])
                self.cursor_line += 1
                self.cursor_col = 0

        elif action == 'BACKSPACE':
            if self.cursor_col > 0:
                self.body_lines[self.cursor_line] = cur[:self.cursor_col - 1] + cur[self.cursor_col:]
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                prev_len = len(self.body_lines[self.cursor_line - 1])
                self.body_lines[self.cursor_line - 1] += cur
                self.body_lines.pop(self.cursor_line)
                self.cursor_line -= 1
                self.cursor_col = prev_len

        elif action == 'DEL':
            if self.cursor_col < len(cur):
                self.body_lines[self.cursor_line] = cur[:self.cursor_col] + cur[self.cursor_col + 1:]
            elif self.cursor_line < len(self.body_lines) - 1:
                self.body_lines[self.cursor_line] = cur + self.body_lines[self.cursor_line + 1]
                self.body_lines.pop(self.cursor_line + 1)

        elif action == 'SPACE' or len(action) == 1:
            if self._total_chars() < self.max_chars:
                char = " " if action == 'SPACE' else action
                self.body_lines[self.cursor_line] = cur[:self.cursor_col] + char + cur[self.cursor_col:]
                self.cursor_col += 1

        if not vertical:
            self._want = None
        self._scroll(layout(self.body_lines, COLS))

    # ------------------------------------------------------------------ drawing

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])

        label = "New" if self.file_index is None else "Edit"
        Lcd.drawString(f"{label}: {self._title()[:20]}", 5, 5)
        renderer.render_keypad_mode_indicator(getattr(self.app, 'keypad', None))
        Lcd.drawRect(5, 22, 230, 88, theme["ACCENT"])

        rows = layout(self.body_lines, COLS)
        row, offset = locate(rows, self.cursor_line, self.cursor_col)
        self.scroll_top = scroll_to(self.scroll_top, row, ROWS, len(rows))

        Lcd.setTextColor(theme["FG"], theme["BG"])
        for i in range(ROWS):
            index = self.scroll_top + i
            if index >= len(rows):
                break
            line_no, start, end = rows[index]
            Lcd.drawString(self.body_lines[line_no][start:end], TEXT_X, TEXT_Y + i * ROW_H)

        if self.scroll_top <= row < self.scroll_top + ROWS:      # the cursor: a bar under the character
            Lcd.fillRect(TEXT_X + 6 * offset, TEXT_Y + (row - self.scroll_top) * ROW_H + 10, 6, 2, theme["ACCENT"])
        Lcd.setTextColor(theme["ACCENT"], theme["BG"])
        if self.scroll_top > 0:                                   # more text above / below
            Lcd.drawString("^", 227, 25)
        if self.scroll_top + ROWS < len(rows):
            Lcd.drawString("v", 227, 25 + (ROWS - 1) * ROW_H)

        Lcd.setTextColor(theme["FG"], theme["BG"])
        if self.menu_name == "MIND":
            Lcd.drawString("CTRL+S = move to Notes", 5, 115)
        else:
            Lcd.drawString("[CTRL+S] Save | [ESC] Discard", 5, 115)
        counter = "%d/%d" % (self._total_chars(), self.max_chars)
        Lcd.drawString(counter, 235 - 6 * len(counter), 115)
