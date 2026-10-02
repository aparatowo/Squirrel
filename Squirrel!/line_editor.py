# line_editor.py - single-line text editing with a cursor (no screen, no hardware)
#
# handle(action) understands the action names the keypad delivers in text mode:
# a single character, SPACE, BACKSPACE (before the cursor), DEL (after it), LEFT, RIGHT.
# ENTER and ESC are left to the caller.


class LineEditor:
    def __init__(self, text="", max_len=32, secret=False):
        self.buf = text[:max_len]
        self.cur = len(self.buf)
        self.max_len = max_len
        self.secret = secret

    def handle(self, action):
        """Apply one key.  Returns True if it changed the text or moved the cursor."""
        if action == 'LEFT':
            moved = self.cur > 0
            self.cur = max(0, self.cur - 1)
            return moved
        if action == 'RIGHT':
            moved = self.cur < len(self.buf)
            self.cur = min(len(self.buf), self.cur + 1)
            return moved
        if action == 'BACKSPACE':
            if self.cur == 0:
                return False
            self.buf = self.buf[:self.cur - 1] + self.buf[self.cur:]
            self.cur -= 1
            return True
        if action == 'DEL':
            if self.cur >= len(self.buf):
                return False
            self.buf = self.buf[:self.cur] + self.buf[self.cur + 1:]
            return True
        char = " " if action == 'SPACE' else (action if len(action) == 1 else None)
        if char is None or len(self.buf) >= self.max_len:
            return False
        self.buf = self.buf[:self.cur] + char + self.buf[self.cur:]
        self.cur += 1
        return True

    def view(self, width=35):
        """The text with a '|' at the cursor, scrolled so that the cursor stays visible.

        A secret is shown as asterisks.
        """
        shown = "*" * len(self.buf) if self.secret else self.buf
        start = max(0, self.cur - (width - 1))
        return shown[start:self.cur] + "|" + shown[self.cur:start + width]
