# screens/clock_screen.py
#
# Shortcuts on this screen (modifier keys arrive as ordinary keys here):
#   OPT  - start / pause the focus timer
#   Aa   - Mind Dump (quick note; ESC / saving returns here)
#   G0   - quick voice recorder (handled by the app, works from here too)
#   any other key - open the menu
import time
from screens.base_screen import BaseScreen

_NOTICE_MS = 1500
FOCUS_KEY = 'OPT'         # start / pause the focus timer
MIND_DUMP_KEY = 'Aa'      # open Mind Dump
_FOCUS_MESSAGES = {
    "started": "Focus ON",
    "resumed": "Focus resumed",
    "paused": "Focus paused",
    "no_time": "Set time first!",
}


class ClockScreen(BaseScreen):
    modifiers_as_keys = True
    quick_record_from = True       # G0 may start the quick recorder from this screen
    shows_focus_dot = False        # the main screen has the bars instead
    shows_bars = True              # vertical status bars: battery (left), focus progress (right)

    def __init__(self, app):
        super().__init__(app)
        self._shown_time = None     # HH:MM currently on the display
        self._notice = None         # short message drawn over the clock
        self._notice_until = 0

    def on_enter(self, **kwargs):
        self._notice = None

    def _notify(self, text):
        self._notice = text
        self._notice_until = time.ticks_add(time.ticks_ms(), _NOTICE_MS)

    def handle_input(self, action):
        if action in ('FN', 'CTRL', 'ALT'):
            return                                      # nothing bound to these here
        if action == FOCUS_KEY:
            self._notify(_FOCUS_MESSAGES[self.app.focus.toggle()])
            return
        if action == MIND_DUMP_KEY:
            self.app.set_screen("MIND_DUMP", return_to=("CLOCK", {}))
            return
        print(f"[NAV] CLOCK -> MENU (MAIN) on key: '{action}'")
        self.app.set_screen("MENU", menu_name="MAIN")

    def needs_refresh(self):
        if self._notice is not None and time.ticks_diff(time.ticks_ms(), self._notice_until) >= 0:
            return True                                 # notice expired: redraw without it
        return self.app.rtc.get_time_str() != self._shown_time

    def render(self, renderer):
        date_str = self.app.rtc.get_date_str()
        time_str = self.app.rtc.get_time_str()
        self._shown_time = time_str
        renderer.render_clock(date_str=date_str, time_str=time_str)
        if self._notice is not None:
            if time.ticks_diff(time.ticks_ms(), self._notice_until) < 0:
                renderer.render_options(self._notice)
            else:
                self._notice = None
