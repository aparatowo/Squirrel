# screens/base_screen.py

class BaseScreen:
    def __init__(self, app):
        self.app = app

    def on_enter(self, **kwargs):
        pass

    def on_exit(self):
        pass

    def handle_input(self, action: str):
        pass

    def render(self, renderer):
        pass

    def needs_refresh(self):
        """Return True when the screen wants a redraw without any key press.

        The main loop calls this every iteration; screens with live content
        (clock, recording timer) override it.  Keep it cheap and return True
        only when the picture would actually change.
        """
        return False