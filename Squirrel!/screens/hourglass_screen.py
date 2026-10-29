# screens/hourglass_screen.py - the hourglass: a countdown timer (Focus tools -> Hourglass)
#
# set:      UP/DOWN one minute more / less, LEFT/RIGHT five, digits type the minutes, ENTER start, ESC back
# running:  ENTER pause / resume      DEL stop      ESC leave (it keeps running: the clock's top bar shows it)
# When it runs out a notification rings (hourglass.py).  The minutes are remembered (HOURGLASS_MIN).
# On a touch screen (the watch): the whole panel - the minutes between "-" and "+" (held: faster), Start; while it
# runs the time left in big letters with Pause / Stop; a tap on the title (or a swipe right) leaves, it keeps running.

from gfx import Lcd
from appconfig import cfg
from nuts import named_color
from screens.base_screen import BaseScreen
from ui.touch import has_touch, TouchList, TouchPanel, Button, header_tapped, button_height, draw_centered
from i18n import _

MIN_MIN, MAX_MIN = 1, 240                   # the range of HOURGLASS_MIN (appconfig_schema.py)


def fmt(seconds):
    """"MM:SS", or "H:MM:SS" from an hour up."""
    h, rest = divmod(seconds, 3600)
    return "%d:%02d:%02d" % (h, rest // 60, rest % 60) if h else "%02d:%02d" % (rest // 60, rest % 60)


class HourglassScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)
        self._minutes = cfg.get("HOURGLASS_MIN")
        self._typed = ""                    # digits typed so far (a new number starts with the first one)
        self._drawn = None
        self._touch = has_touch()
        self._panel = TouchPanel() if self._touch else None
        self._list = TouchList() if self._touch else None

    @property
    def full_height(self):
        return self._touch

    @property
    def hourglass(self):
        return self.app.hourglass()

    def on_enter(self, **kwargs):
        self._minutes = cfg.get("HOURGLASS_MIN")
        self._typed = ""
        self._drawn = None

    def _state(self):
        hg = self.hourglass
        return hg.state, hg.remaining(), self._minutes

    def needs_refresh(self):
        if self._touch and self._panel.tick(self.app.keypad):
            return True
        return self._state() != self._drawn

    def _change(self, delta):
        self._typed = ""
        self._minutes = max(MIN_MIN, min(MAX_MIN, self._minutes + delta))

    def _type(self, digit):
        self._typed = (self._typed + digit)[-3:].lstrip("0")
        if self._typed:
            self._minutes = max(MIN_MIN, min(MAX_MIN, int(self._typed)))

    def _start(self):
        self._typed = ""
        if cfg.get("HOURGLASS_MIN") != self._minutes:
            cfg.set("HOURGLASS_MIN", self._minutes)          # remembered for the next time
        self.hourglass.start(self._minutes * 60)

    def _leave(self):
        self.app.set_screen("MENU", menu_name="FOCUS")

    # ---------------------------------------------------------------- input

    def handle_input(self, action):
        hg = self.hourglass
        if self._touch:
            if action in ('ESC', 'LEFT') or (action in ('ENTER', 'OPT') and header_tapped(self.app.keypad)):
                self._leave()
            else:
                self._panel.handle(action, self.app.keypad)
            return
        if hg.state in ("running", "paused"):
            if action == 'ENTER':
                hg.toggle()
            elif action == 'DEL':
                hg.stop()
            elif action in ('ESC', 'LEFT'):
                self._leave()
            return
        if hg.state == "done":
            if action in ('ENTER', 'ESC', 'DEL'):
                hg.stop()
            return
        if action == 'ENTER':
            self._start()
        elif action in ('UP', 'DOWN'):
            self._change(1 if action == 'UP' else -1)
        elif action in ('LEFT', 'RIGHT'):
            self._change(5 if action == 'RIGHT' else -5)
        elif isinstance(action, str) and len(action) == 1 and action.isdigit():
            self._type(action)
        elif action in ('ESC', 'BACKSPACE'):
            self._leave()

    # ---------------------------------------------------------------- drawing

    def _status(self, state):
        return _({"running": "RUNNING", "paused": "PAUSED", "done": "FINISHED"}[state]) if state != "idle" else ""

    def _progress_line(self, theme, x0, y, width, cell=6):
        """The time gone by as a row of '#', coloured like the clock's top bar."""
        hg = self.hourglass
        cells = max(1, width // cell)
        done = hg.elapsed_ms() * cells // (hg.total_s * 1000) if hg.state != "idle" and hg.total_s else 0
        Lcd.setTextSize(1)
        Lcd.setTextColor(named_color(cfg.get("BARS_TOP_COLOR")), theme["BG"])
        Lcd.drawString("#" * done, x0, y)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("#" * (cells - done), x0 + cell * done, y)

    def render(self, renderer):
        self._drawn = self._state()
        if self._touch:
            return self._render_touch(renderer)
        theme = renderer.theme
        hg = self.hourglass
        state = hg.state
        renderer.clear()
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(_("Hourglass"), 5, 5)
        status = self._status(state)
        if status:
            Lcd.setTextColor(theme["WARNING"] if state != "running" else theme["ACCENT"], theme["BG"])
            Lcd.drawString(status, 235 - 6 * len(status), 5)                # to the right edge, whatever its length
        text = fmt(self._minutes * 60) if state == "idle" else fmt(hg.remaining())
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.setTextSize(4)
        Lcd.drawString(text, max(0, (240 - 24 * len(text)) // 2), 30)
        Lcd.setTextSize(1)
        if state == "idle":
            Lcd.drawString(_("up/down 1 min  <> 5 min  0-9 minutes"), 5, 90)
            footer = _("[ENTER] %s  [ESC] Back") % _("Start")
        else:
            self._progress_line(theme, 6, 78, 228)
            footer = (_("[ENTER] Close") if state == "done" else
                      _("[ENTER] %s  [DEL] Stop") % (_("Resume") if state == "paused" else _("Pause")))
        Lcd.setTextColor(theme["ACCENT"], theme["BG"])
        Lcd.drawString(footer, 5, 118)

    def _render_touch(self, renderer):
        theme = renderer.theme
        hg = self.hourglass
        state = hg.state
        renderer.clear()
        w, h = Lcd.screen_size()
        top = TouchList.HEADER
        self._list.draw_header(theme, _("Hourglass"), self._status(state) or None)
        bh = button_height()
        p = self._panel
        p.clear()
        y = h - bh - 2
        if state == "idle":
            y1 = top + 20
            p.add(Button(4, y1, bh, bh, "-"), lambda: self._change(-1), repeat=True)
            p.add(Button(w - 4 - bh, y1, bh, bh, "+"), lambda: self._change(1), repeat=True)
            draw_centered(str(self._minutes), y1 + (bh - 40) // 2, 5, theme["FG"], theme["BG"], max_w=w - 2 * (bh + 12))
            draw_centered(_("minutes"), y1 + bh + 10, 2, theme["FG"], theme["BG"])
            p.add(Button(4, y, w - 8, bh, _("Start"), "ACCENT"), self._start)
        else:
            draw_centered(fmt(hg.remaining()), top + 30, 6, theme["FG"], theme["BG"], max_w=w - 8)
            self._progress_line(theme, 6, top + 100, w - 12)
            if state == "done":
                p.add(Button(4, y, w - 8, bh, _("Close"), "ACCENT"), hg.stop)
            else:
                half = w // 2
                p.add(Button(4, y, half - 8, bh, _("Resume") if state == "paused" else _("Pause"), "ACCENT"), hg.toggle)
                p.add(Button(half + 4, y, half - 8, bh, _("Stop"), "ERROR"), hg.stop)
        p.draw(theme)
