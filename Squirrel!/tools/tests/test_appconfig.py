# tools/tests/test_appconfig.py - config.txt: an old default written by an older version gives way to the new one
import os
import sys
import tempfile
sys.path.insert(0, ".")
import time
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_add = lambda a, b: a + b
    time.ticks_diff = lambda a, b: a - b
import appconfig

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


path = os.path.join(tempfile.mkdtemp(), "config.txt")
import nuts
nuts.CLOCK_FOOTER_TEXT = "Squirrel! is watching"            # a watch's default
c = appconfig.Config()
with open(path, "w") as f:
    f.write("CLOCK_FOOTER_TEXT = no need to go nuts\nFOCUS_GOAL_MINUTES = 120\n")
c.load(path)
check("an old default becomes the new one", c.get("CLOCK_FOOTER_TEXT") == "Squirrel! is watching")
check("other settings read as written", c.get("FOCUS_GOAL_MINUTES") == 120)
with open(path, "w") as f:
    f.write("CLOCK_FOOTER_TEXT = my own motto\n")
c.load(path)
check("a text of the user's own stays", c.get("CLOCK_FOOTER_TEXT") == "my own motto")

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
