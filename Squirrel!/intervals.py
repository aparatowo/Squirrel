# intervals.py - timers made of blocks (Pomodoro, Training) and the metronome
#
# Loaded when first needed (the app creates the services on demand and keeps them running in the background).
# A plan is a list of [colour, seconds] blocks.  Colours and what they mean in a training:
#   blue = preparation, yellow = light effort, orange = normal effort, red = increased effort, green = rest / the end.
# The screens that drive these are screens/interval_screen.py and screens/rhythm_screens.py.

import json
import time
import nuts
from boot_log import log

COLORS = ("blue", "yellow", "orange", "red", "green")
NAMES = {"blue": "Prepare", "yellow": "Light", "orange": "Normal", "red": "Hard", "green": "Rest"}
SOUND = {"blue": "step", "yellow": "step", "orange": "go", "red": "go", "green": "rest"}
MIN_S, MAX_S = 5, nuts.MAX_BLOCK_SECONDS
METRO_STEPS = (1, 2, 5, 30, 60, 120)
DEFAULT_TRAINING = [["blue", 120], ["yellow", 180], ["orange", 180], ["red", 60], ["green", 60],
                    ["red", 60], ["green", 60], ["green", 120]]


def fmt(seconds):
    return "%d:%02d" % (seconds // 60, seconds % 60)


def step_for(seconds):
    """How much one key press changes a block's time: fine for short blocks, coarse for long ones."""
    return 5 if seconds < 60 else (15 if seconds < 300 else 60)


def change_seconds(seconds, direction):
    return max(MIN_S, min(MAX_S, seconds + direction * step_for(seconds if direction > 0 else seconds - 1)))


def pomodoro_plan(cfg):
    cycles = cfg.get("POMODORO_CYCLES")
    plan = []
    for n in range(cycles):
        plan.append(["red", cfg.get("POMODORO_WORK_MIN") * 60])
        plan.append(["green", (cfg.get("POMODORO_LONG_BREAK_MIN") if n == cycles - 1 else cfg.get("POMODORO_BREAK_MIN")) * 60])
    return plan


def load_training(path):
    try:
        with open(path) as f:
            data = json.loads(f.read())
        plan = [[c, max(MIN_S, min(MAX_S, int(s)))] for c, s in data if c in COLORS]
        if plan:
            return plan
    except (OSError, ValueError, TypeError):
        pass
    return [list(b) for b in DEFAULT_TRAINING]


def save_training(path, plan):
    try:
        with open(path, "w") as f:
            f.write(json.dumps(plan))
        return True
    except OSError as e:
        log(f"[TRAINING] cannot save: {e}")
        return False


class IntervalRunner:
    """Service: runs a plan block by block, with a signal at every change and a notification at the end."""

    def __init__(self, audio, notifier, now_ms=None):
        self._audio = audio
        self._notifier = notifier
        self._now = now_ms or time.ticks_ms
        self.state = "idle"            # idle | running | paused | done
        self.plan = []
        self.title = ""
        self.index = 0
        self._elapsed = 0              # ms into the current block
        self._last = 0

    def start(self, plan, title):
        self.plan, self.title = [list(b) for b in plan], title
        self.index, self._elapsed, self._last = 0, 0, self._now()
        self.state = "running"
        self._signal()

    def toggle(self):
        if self.state == "running":
            self._account()
            self.state = "paused"
        elif self.state == "paused":
            self._last = self._now()
            self.state = "running"

    def stop(self):
        self.state = "idle"

    def _signal(self):
        self._audio.beep(SOUND[self.plan[self.index][0]])

    def _account(self):
        now = self._now()
        self._elapsed += time.ticks_diff(now, self._last)
        self._last = now

    def tick(self):
        if self.state != "running":
            return
        self._account()
        while self._elapsed >= self.plan[self.index][1] * 1000:
            self._elapsed -= self.plan[self.index][1] * 1000
            self.index += 1
            if self.index >= len(self.plan):
                self._finish()
                return
            self._signal()

    def _finish(self):
        self.state = "done"
        self.index = len(self.plan) - 1
        self._audio.beep("notify")
        from notifier import Notification
        self._notifier.post(Notification(self.title + " finished", title=self.title, timeout_s=20,
                                         done_label="OK", cancel_label="Close"))

    # ---- what the screen shows ----
    def remaining(self):
        """Whole seconds left in the current block."""
        if not self.plan:
            return 0
        left = self.plan[self.index][1] * 1000 - self._elapsed
        return max(0, (left + 999) // 1000)

    def total(self):
        return sum(b[1] for b in self.plan)


class Metronome:
    """Service: a tick every `interval` seconds.  A recording closes it (the tick would be in the recording)."""

    def __init__(self, audio, cfg, now_ms=None):
        self._audio = audio
        self._cfg = cfg
        self._now = now_ms or time.ticks_ms
        self.running = False
        self.beats = 0
        self._next = 0

    def start(self):
        self.running = True
        self._next = self._now()

    def stop(self):
        self.running = False

    def tick(self):
        if not self.running:
            return
        if self._audio.is_recording():
            self.running = False
            return
        if time.ticks_diff(self._now(), self._next) >= 0:
            self._audio.beep("tick" if self.beats % 4 else "tock", volume=self._cfg.get("METRO_VOLUME"))
            self.beats += 1
            self._next = time.ticks_add(self._next, self._cfg.get("METRO_INTERVAL_S") * 1000)