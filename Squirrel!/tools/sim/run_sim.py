# run_sim.py - runs Squirrel! on the PC under the MicroPython unix port, with fake hardware, and writes a trace
#
#   micropython tools/sim/run_sim.py <app dir> <empty work dir> <trace file> [port]
#
# The trace holds every display call, every key and the boot log, in order; the work dir ends up holding what the app
# wrote to /sd and /flash.  Two versions of the code that behave the same give identical traces and files - that is
# how a refactoring is checked without the device (tools/sim/compare.sh).  The clock is fake and only moves when the
# code sleeps, so a run is fully repeatable.

import sys
import builtins

APP, ROOT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = sys.argv[0].rpartition("/")[0] or "."
sys.path[:0] = [HERE + "/fakes", APP]

import sim_state as S
S.root = ROOT

_open = builtins.open


def _sim_open(path, *a, **k):
    import os
    return _open(os._p(path), *a, **k)


builtins.open = _sim_open

import os
for d in ("/sd", "/sd/Squirrel", "/flash", "/system"):
    try:
        os.mkdir(d)
    except OSError:
        pass

# key codes of the Cardputer matrix (nuts.MAP_NAV)
CODES = {"ESC": 1, "TAB": 2, "FN": 3, "CTRL": 4, "Aa": 7, "OPT": 8, "ALT": 14, "BACKSPACE": 65, "ENTER": 67,
         "UP": 57, "DOWN": 58, "LEFT": 54, "RIGHT": 64, "SPACE": 68}
for ch, code in zip("1234567890", (5, 11, 15, 21, 25, 31, 35, 41, 45, 51)):
    CODES[ch] = code
for ch, code in zip("qwertyuiopasdfghjklzxcvbnm",
                    (6, 12, 16, 22, 26, 32, 36, 42, 46, 52, 13, 17, 23, 27, 33, 37, 43, 47, 53, 18, 24, 28, 34, 38, 44, 48)):
    CODES[ch] = code

import boot_log
boot_log.begin_session()
try:                                  # the way squirrel_boot.py starts the hardware
    import port_config
    __import__(port_config.BOARD_MODULE, None, None, ("begin",)).begin()
except ImportError:                   # code from before the ports (it called M5.begin() itself)
    import M5
    M5.begin()
from squirrel_app import SquirrelApp

app = SquirrelApp()
S.trace.append("--- constructed ---")
app._apply_screen_input_mode()
app._render_active()


def step(n=1):
    for _ in range(n):
        try:
            app._step()
        except Exception as e:
            app._recover_from_error(e)
        power = app.power
        if power is None or not power.maybe_sleep():
            S.ms += power.pause_ms() if power else 20


def key(name):
    S.trace.append("KEY %s @%d" % (name, S.ms))
    code = CODES[name]
    S.keys.append(0x80 | code)
    step(2)
    S.keys.append(code)
    step(3)


def type_text(text):
    for ch in text:
        if ch == " ":
            key("SPACE")
        else:
            key(ch)


def button0():
    S.trace.append("BTN0 @%d" % S.ms)
    S.button0 = 0
    step(4)
    S.button0 = 1
    step(4)


def at_clock():
    return app.active_screen is app.screens["CLOCK"] and app.overlay is None


def awake():
    if app.dimmer.dimmed:
        key("ESC")                 # the key that wakes the screen does nothing else


def home():
    """Back to the clock with ESC, as a user would; a screen that does not let go is left through the app."""
    awake()
    for _ in range(8):
        if at_clock():
            break
        key("ESC")
    if not at_clock():
        S.trace.append("HOME forced from %s" % type(app.active_screen).__name__)
        if app.overlay is not None:
            app.hide_overlay()
        app.set_screen("CLOCK")
    step(5)


def visit(path, wait=40, extra=()):
    """From the clock: open the main menu, go down the path of entry indexes (ENTER on each), wait, back home."""
    S.trace.append("== visit %s ==" % (path,))
    home()
    key("ENTER")
    for index in path:
        for _ in range(index):
            key("DOWN")
        key("ENTER")
    step(wait)
    for k in extra:
        if k.startswith("TYPE:"):
            type_text(k[5:])
        elif k.startswith("W:"):
            step(int(k[2:]))
        else:
            key(k)
    home()


from menu_tree import MENUS


def walk(menu_id, prefix, out, skip):
    entries = MENUS[menu_id][1]
    for i, entry in enumerate(entries):
        path = prefix + [i]
        target = entry[2] if not isinstance(entry[2], tuple) else entry[2][0]
        if target in skip:
            continue
        if entry[1] == "menu" and entry[2] in MENUS:
            walk(entry[2], path, out, skip)
        else:
            out.append(path)


SKIP = ("FONT_TEST",)             # its countdown ends in machine.reset()

step(50)
# 1. every entry of every menu, one at a time
paths = []
walk("MAIN", [], paths, SKIP)
for p in paths:
    visit(p)

# 2. To-Do: a new item, saved with CTRL+S, marked done (OPT), opened
visit([2, 0], extra=("TYPE:kupic orzechy", "CTRL", "s", "W:20", "DOWN", "OPT", "W:20", "ENTER", "W:20"))
# 3. A text note, saved
visit([1, 0, 0], extra=("TYPE:pierwsza linia", "ENTER", "TYPE:druga", "CTRL", "s", "W:20"))
# 4. Mind Dump from the clock
S.trace.append("== mind dump ==")
home()
key("Aa")
type_text("szybka mysl")
key("ENTER")
step(20)
home()
# 5. Focus timer on the clock, time passes, the screen dims and wakes
home()
key("OPT")
step(400)
key("SPACE")
step(20)
awake()
key("OPT")
home()
# 6. The quick recorder from the clock (G0 twice)
home()
button0()
step(80)
button0()
step(40)
home()
# 6b. The take just recorded, played back from Voice Notes
visit([1, 2], wait=10, extra=("DOWN", "ENTER", "W:150", "ENTER", "W:20", "ESC", "W:10"))
# 7. Pomodoro started, a long wait (blocks end, notifications come), then stopped
visit([0, 2], wait=10, extra=("ENTER", "W:3000", "ESC", "W:20"))
# 8. A minute and a half of idling on the clock
step(4500)

S.trace.append("--- end @%d ---" % S.ms)
with _open(OUT, "w") as f:
    for line in S.trace:
        f.write(line + "\n")
print("SIM DONE", len(S.trace), "trace lines, ms =", S.ms)
