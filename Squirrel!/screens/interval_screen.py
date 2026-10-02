# screens/interval_screen.py - Pomodoro and Training: a row of coloured blocks, counted down one after another
#
# Opened with mode="pomodoro" (work / break from the settings) or mode="training" (the blocks you put together).
# The timer is a background service: leaving the screen does not stop it.
#
# ready:    ENTER start      training: RIGHT edit the blocks         ESC back
# running:  ENTER pause / resume      DEL stop      ESC leave (it keeps running)
# editing:  UP/DOWN block   LEFT/RIGHT shorter / longer   ENTER next colour   DEL remove   ESC save and leave

from gfx import Lcd
import nuts
import intervals as iv
from appconfig import cfg
from screens.base_screen import BaseScreen

_VISIBLE = 5


class IntervalScreen(BaseScreen):
    keeps_screen_on = True

    def __init__(self, app):
        super().__init__(app)
        self.mode = "pomodoro"
        self.editing = False
        self.plan = []
        self.i = 0
        self.top = 0
        self._drawn = None

    def on_enter(self, mode="pomodoro", **kwargs):
        self.mode, self.editing, self.i, self.top = mode, False, 0, 0
        self.plan = iv.pomodoro_plan(cfg) if mode == "pomodoro" else iv.load_training(nuts.TRAINING_FILE)
        self._drawn = None

    @property
    def runner(self):
        return self.app.runner()

    def _label(self):
        return "Pomodoro" if self.mode == "pomodoro" else "Training"

    def needs_refresh(self):
        r = self.runner
        return (r.state, r.index, r.remaining()) != self._drawn

    # ---------------------------------------------------------------- input

    def handle_input(self, action):
        if self.editing:
            self._edit_input(action)
            return
        r = self.runner
        if r.state in ("running", "paused"):
            if action == 'ENTER':
                r.toggle()
            elif action == 'DEL':
                r.stop()
            elif action in ('ESC', 'LEFT'):
                self.app.set_screen("MENU", menu_name="FOCUS")
            return
        if action == 'ENTER':
            if r.state == "done":
                r.stop()
            else:
                r.start(self.plan, self._label())
        elif action == 'RIGHT' and self.mode == "training":
            self.editing, self.i, self.top = True, 0, 0
        elif action in ('ESC', 'LEFT'):
            r.stop()
            self.app.set_screen("MENU", menu_name="FOCUS")

    def _edit_input(self, action):
        rows = len(self.plan) + 1                                   # row 0 is "+ add block"
        if action in ('UP', 'DOWN'):
            self.i = (self.i + (-1 if action == 'UP' else 1)) % rows
            if self.i < self.top:
                self.top = self.i
            elif self.i >= self.top + _VISIBLE:
                self.top = self.i - _VISIBLE + 1
            self.top = max(0, min(self.top, max(0, rows - _VISIBLE)))
        elif action == 'ENTER':
            if self.i == 0:
                if len(self.plan) < 30:
                    self.plan.append(["orange", 60])
                    self.i = len(self.plan)
                    self.top = max(0, self.i - _VISIBLE + 1)
            else:
                block = self.plan[self.i - 1]
                block[0] = iv.COLORS[(iv.COLORS.index(block[0]) + 1) % len(iv.COLORS)]
        elif action in ('LEFT', 'RIGHT') and self.i > 0:
            block = self.plan[self.i - 1]
            block[1] = iv.change_seconds(block[1], 1 if action == 'RIGHT' else -1)
        elif action == 'DEL' and self.i > 0 and len(self.plan) > 1:
            del self.plan[self.i - 1]
            self.i = min(self.i, len(self.plan))
        elif action == 'ESC':
            iv.save_training(nuts.TRAINING_FILE, self.plan)
            self.editing = False

    # ---------------------------------------------------------------- drawing

    def _strip(self, plan, current, theme):
        total = sum(b[1] for b in plan) or 1
        x = 5
        for n, (color, secs) in enumerate(plan):
            w = max(3, secs * 226 // total)
            Lcd.fillRect(x, 92, w - 1, 12, nuts.named_color(color))
            if n == current:
                Lcd.drawRect(x - 1, 90, w + 1, 16, theme["FG"])
            x += w

    def render(self, renderer):
        theme = renderer.theme
        if self.editing:
            rows = ["+ [Add block]"] + ["%d. %-7s %s" % (n + 1, iv.NAMES[c], iv.fmt(s)) for n, (c, s) in enumerate(self.plan)]
            renderer.render_menu("Training blocks", rows, self.i, self.top, _VISIBLE)
            if self.i > 0:
                Lcd.setTextColor(nuts.named_color(self.plan[self.i - 1][0]), theme["BG"])
                Lcd.drawString("####", 200, 124)
            return
        r = self.runner
        active = r.state != "idle"
        plan = r.plan if active else self.plan
        self._drawn = (r.state, r.index, r.remaining())
        renderer.clear()
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(r.title if active else self._label(), 5, 5)
        if not active:
            Lcd.drawString("%d blocks, %s in all" % (len(plan), iv.fmt(sum(b[1] for b in plan))), 5, 24)
            self._strip(plan, -1, theme)
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            Lcd.drawString("[ENTER] Start" + ("   [RIGHT] Edit" if self.mode == "training" else ""), 5, 118)
            return
        color, secs = plan[r.index]
        Lcd.setTextColor(nuts.named_color(color), theme["BG"])
        Lcd.setTextSize(2)
        Lcd.drawString(iv.NAMES[color], 5, 20)
        Lcd.setTextSize(3)
        Lcd.drawString(iv.fmt(r.remaining()), 5, 44)
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        tag = {"running": "RUNNING", "paused": "PAUSED", "done": "FINISHED"}[r.state]
        Lcd.drawString("%s  block %d/%d" % (tag, r.index + 1, len(plan)), 150, 5)
        if r.state != "done" and r.index + 1 < len(plan):
            nxt = plan[r.index + 1]
            Lcd.drawString("Next: %s %s" % (iv.NAMES[nxt[0]], iv.fmt(nxt[1])), 5, 76)
        self._strip(plan, r.index, theme)
        Lcd.setTextColor(theme["ACCENT"], theme["BG"])
        Lcd.drawString("[ENTER] %s  [DEL] Stop" % ("Resume" if r.state == "paused" else "Pause") if r.state != "done" else "[ENTER] Close", 5, 118)
