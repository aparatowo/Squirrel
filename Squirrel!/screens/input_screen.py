# screens/input_screen.py
from screens.base_screen import BaseScreen


class InputScreen(BaseScreen):
    """Generic text input screen.

    Parameters
    ----------
    multiline : bool
        When True (default) ENTER inserts a newline and CTRL+S saves.
        When False (single-line mode) ENTER saves directly — useful for
        short prompts where a line-break makes no sense (e.g. a title field).
    """

    def __init__(self, app):
        super().__init__(app)
        self.prompt = ""
        self.max_chars = 160
        self.callback = None
        self.text_buffer = ""
        self.multiline = True

    def on_enter(self, prompt="Enter text:", max_chars=160, callback=None,
                 initial_text="", multiline=True, **kwargs):
        self.prompt = prompt
        self.max_chars = max_chars
        self.callback = callback
        self.text_buffer = initial_text
        self.multiline = multiline
        if hasattr(self.app, 'keypad'):
            self.app.keypad.set_text_mode(True)

    def _submit(self):
        """Fire the callback and exit text-input mode."""
        cb = self.callback
        self.callback = None
        if hasattr(self.app, 'keypad'):
            self.app.keypad.set_text_mode(False)
        if cb:
            cb(self.text_buffer)

    def handle_input(self, action):
        if not action:
            return

        # --- Save / Submit ---
        if action in ('CTRL+s', 'CTRL+S'):
            # CTRL+S always saves, regardless of multiline flag
            self._submit()

        elif action == 'ENTER':
            if self.multiline:
                # In multiline mode ENTER = newline character
                if len(self.text_buffer) < self.max_chars:
                    self.text_buffer += "\n"
            else:
                # In single-line mode ENTER = confirm/save
                self._submit()

        # --- Cancel ---
        elif action in ('ESC', 'CTRL+ESC', 'FN+ESC'):
            if hasattr(self.app, 'keypad'):
                self.app.keypad.set_text_mode(False)
            self.app.set_screen("MENU")

        # --- Editing ---
        elif action in ('BS', 'BACKSPACE'):
            if len(self.text_buffer) > 0:
                self.text_buffer = self.text_buffer[:-1]

        elif action == 'SPACE':
            if len(self.text_buffer) < self.max_chars:
                self.text_buffer += " "

        else:
            if len(action) == 1 and len(self.text_buffer) < self.max_chars:
                self.text_buffer += action

    def render(self, renderer):
        keypad = getattr(self.app, 'keypad', None)
        renderer.render_input_prompt(self.prompt, self.text_buffer, keypad)