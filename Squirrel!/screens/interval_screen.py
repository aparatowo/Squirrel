# screens/interval_screen.py - Pomodoro and Training: a row of coloured blocks, counted down one after another
#
# Opened with mode="pomodoro" (work / break from the settings) or mode="training" (the blocks you put together).
# The timer is a background service: leaving the screen does not stop it.
#
# ready:    ENTER start      training: RIGHT edit the blocks         ESC back
# running:  ENTER pause / resume      DEL stop      ESC leave (it keeps running)
# editing:  UP/DOWN block   LEFT/RIGHT shorter / longer   ENTER next colour   DEL remove   ESC save and leave
# On a touch screen (the watch): the whole panel - the block's name and the time left in big letters, the blocks as a
# strip, Start / Pause / Stop as buttons; a tap on the title (or a swipe right) leaves, the timer keeps running.  The
# training blocks are put together on the Cardputer (they come over the sync).

from gfx import Lcd
import nuts
import intervals as iv
from appconfig import cfg
from screens.base_screen import BaseScreen
from ui.touch import has_touch, TouchList, TouchPanel, Button, header_tapped, button_height, draw_centered
from i18n import _
from charmap import pad

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
        self._touch = has_touch()
        self._panel = TouchPanel() if self._touch else None
        self._list = TouchList() if self._touch else None

    @property
    def full_height(self):
        return self._touch

    def on_enter(self, mode="pomodoro", **kwargs):
        self.mode, self.editing, self.i, self.top = mode, False, 0, 0
        self.plan = iv.pomodoro_plan(cfg) if mode == "pomodoro" else iv.load_training(nuts.TRAINING_FILE)
        self._drawn = None

    @property
    def runner(self):
        return self.app.runner()

    def _pomodoro(self, r):
        """Is what runs (or is about to) a Pomodoro?  Its blocks are work / break, not training efforts."""
        return (r.title == "Pomodoro") if r.state != "idle" else self.mode == "pomodoro"

    def _label(self):
        return "Pomodoro" if self.mode == "pomodoro" else "Training"

    def needs_refresh(self):
        r = self.runner
        return (r.state, r.index, r.remaining()) != self._drawn

    # ---------------------------------------------------------------- input

    def handle_input(self, action):
        if self._touch:
            if action in ('ESC', 'LEFT') or (action in ('ENTER', 'OPT') and header_tapped(self.app.keypad)):
                if self.runner.state == "idle":
                    self.runner.stop()
                self.app.set_screen("MENU", menu_name="FOCUS")
            else:
                self._panel.handle(action, self.app.keypad)
            return
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

    def _strip_at(self, plan, current, theme, x0, width, y, h):
        total = sum(b[1] for b in plan) or 1
        x = x0
        for n, (color, secs) in enumerate(plan):
            w = max(3, secs * width // total)
            Lcd.fillRect(x, y, w - 1, h, nuts.named_color(color))
            if n == current:
                Lcd.drawRect(x - 1, y - 2, w + 1, h + 4, theme["FG"])
            x += w

    def _touch_buttons(self, r):
        w, h = Lcd.screen_size()
        bh = button_height()
        y = h - bh - 2
        p = self._panel
        p.clear()
        if r.state == "idle":
            p.add(Button(4, y, w - 8, bh, _("Start"), "ACCENT"), lambda: r.start(self.plan, self._label()))
        elif r.state == "done":
            p.add(Button(4, y, w - 8, bh, _("Close"), "ACCENT"), r.stop)
        else:
            half = w // 2
            p.add(Button(4, y, half - 8, bh, _("Resume") if r.state == "paused" else _("Pause"), "ACCENT"), r.toggle)
            p.add(Button(half + 4, y, half - 8, bh, _("Stop"), "ERROR"), r.stop)

    def _render_touch(self, renderer):
        theme = renderer.theme
        r = self.runner
        active = r.state != "idle"
        plan = r.plan if active else self.plan
        self._drawn = (r.state, r.index, r.remaining())
        renderer.clear()
        w, h = Lcd.screen_size()
        top = TouchList.HEADER
        self._list.draw_header(theme, _(r.title if active else self._label()),
                               "%d/%d" % (r.index + 1, len(plan)) if active else None)
        if not active:
            draw_centered(_("%d blocks") % len(plan), top + 14, 2, theme["FG"], theme["BG"])
            draw_centered(iv.fmt(sum(b[1] for b in plan)), top + 42, 5, theme["FG"], theme["BG"])
            self._strip_at(plan, -1, theme, 6, w - 12, top + 100, 18)
        else:
            color, _secs = plan[r.index]
            draw_centered(iv.block_name(plan, r.index, self._pomodoro(r)), top + 8, 3, nuts.named_color(color), theme["BG"])
            draw_centered(iv.fmt(r.remaining()), top + 40, 6, theme["FG"], theme["BG"])
            tag = _({"running": "", "paused": "PAUSED", "done": "FINISHED"}[r.state]) if r.state != "running" else ""
            nxt = ""
            if r.state != "done" and r.index + 1 < len(plan):
                nb = plan[r.index + 1]
                nxt = _("next %s %s") % (iv.block_name(plan, r.index + 1, self._pomodoro(r)), iv.fmt(nb[1]))
            draw_centered(tag or nxt, top + 92, 2, theme["WARNING"] if tag else theme["FG"], theme["BG"])
            self._strip_at(plan, r.index, theme, 6, w - 12, top + 120, 18)
        self._touch_buttons(r)
        self._panel.draw(theme)

    def render(self, renderer):
        theme = renderer.theme
        if self._touch:
            return self._render_touch(renderer)
        if self.editing:
            width = max(len(_(name)) for name in iv.NAMES.values())    # the times in one column, in any language
            rows = [_("+ [Add block]")] + ["%d. %s %s" % (n + 1, pad(_(iv.NAMES[c]), width), iv.fmt(s))
                                            for n, (c, s) in enumerate(self.plan)]
            renderer.render_menu(_("Training blocks"), rows, self.i, self.top, _VISIBLE)
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
        Lcd.drawString(_(r.title if active else self._label()), 5, 5)
        if not active:
            Lcd.drawString(_("%d blocks, %s in all") % (len(plan), iv.fmt(sum(b[1] for b in plan))), 5, 24)
            self._strip(plan, -1, theme)
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            Lcd.drawString(_("[ENTER] Start") + (_("   [RIGHT] Edit") if self.mode == "training" else ""), 5, 118)
            return
        color, secs = plan[r.index]
        Lcd.setTextColor(nuts.named_color(color), theme["BG"])
        Lcd.setTextSize(2)
        Lcd.drawString(iv.block_name(plan, r.index, self._pomodoro(r)), 5, 20)
        Lcd.setTextSize(3)
        Lcd.drawString(iv.fmt(r.remaining()), 5, 44)
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        tag = _({"running": "RUNNING", "paused": "PAUSED", "done": "FINISHED"}[r.state])
        status = _("%s  block %d/%d") % (tag, r.index + 1, len(plan))
        Lcd.drawString(status, 235 - 6 * len(status), 5)               # to the right edge, whatever its length
        if r.state != "done" and r.index + 1 < len(plan):
            nxt = plan[r.index + 1]
            Lcd.drawString(_("Next: %s %s") % (iv.block_name(plan, r.index + 1, self._pomodoro(r)), iv.fmt(nxt[1])), 5, 76)
        self._strip(plan, r.index, theme)
        Lcd.setTextColor(theme["ACCENT"], theme["BG"])
        Lcd.drawString(_("[ENTER] %s  [DEL] Stop") % (_("Resume") if r.state == "paused" else _("Pause")) if r.state != "done" else _("[ENTER] Close"), 5, 118)
