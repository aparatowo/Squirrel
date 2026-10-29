# tools/tests/test_button.py - G0 (drivers/gpio_button.py): a press counts once, and a light sleep (polls ~800 ms
# apart) never turns stray low samples into a press - that started the quick recorder by itself (CPython)
import sys
import time
import types
sys.path.insert(0, ".")

clock = [0]
level = [1]
time.ticks_ms = lambda: clock[0]
time.ticks_diff = lambda a, b: a - b
time.ticks_add = lambda a, b: a + b


class Pin:
    IN = 1
    PULL_UP = 2

    def __init__(self, *a):
        pass

    def value(self):
        return level[0]


sys.modules["machine"] = types.SimpleNamespace(Pin=Pin)
from drivers.gpio_button import ButtonPoller

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


def presses(seq):
    clock[0], level[0] = 0, 1
    b = ButtonPoller(0)
    n = 0
    for t, lv in seq:
        clock[0], level[0] = t, lv
        n += b.pressed()
    return n


check("a stray low before a sleep and after the wake", presses([(0, 1), (20, 1), (40, 0), (840, 0), (860, 0),
                                                                  (880, 1), (900, 1)]) == 0)
check("low for 100 ms right after a wake", presses([(0, 1), (800, 0), (820, 0), (860, 0), (900, 0), (920, 1)]) == 0)
check("a real press, held 100 ms", presses([(t, 0 if 100 <= t < 200 else 1) for t in range(0, 400, 20)]) == 1)
check("held through a slow pass of the loop", presses([(0, 1), (20, 0), (180, 0), (200, 0), (320, 0), (340, 1)]) == 1)
check("held at start-up is no press", (lambda: (level.__setitem__(0, 0), ButtonPoller(0).pressed())[1])() is False)

print("FAILED: %s" % ", ".join(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
