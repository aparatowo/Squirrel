# boot_log.py - tiny logger that mirrors messages to /flash/boot_log.txt
#
# After a hardware reset there is no Thonny console, so this file is the only
# way to see what happened during startup.  Each line starts with time.ticks_ms()
# (milliseconds since the chip booted), so the first line of a session also shows
# how long the firmware needed before main.py started.
# Read it with:  print(open('/flash/boot_log.txt').read())

import os
import time

LOG_PATH = "/flash/boot_log.txt"
_KEEP_BYTES = 2000   # tail of previous boots kept when the file grows
_MAX_BYTES = 6000    # when the file reaches this, the oldest lines are dropped (the newest _KEEP_BYTES stay): logging never goes silent


def begin_session():
    """Trim old history (keeping its tail) and mark the start of a boot."""
    try:
        if os.stat(LOG_PATH)[6] > _KEEP_BYTES + 1000:
            with open(LOG_PATH, "r") as f:
                data = f.read()
            tail = data[-_KEEP_BYTES:]
            nl = tail.find("\n")
            if nl >= 0:
                tail = tail[nl + 1:]
            with open(LOG_PATH, "w") as f:
                f.write(tail)
    except OSError:
        pass
    log("--- boot ---")


def _rotate():
    """Keep the newest _KEEP_BYTES of the log (from a whole line on) and drop the rest."""
    try:
        with open(LOG_PATH, "r") as f:
            data = f.read()
        tail = data[-_KEEP_BYTES:]
        nl = tail.find("\n")
        if nl >= 0:
            tail = tail[nl + 1:]
        with open(LOG_PATH, "w") as f:
            f.write(tail)
    except Exception:
        pass


def log(msg):
    """Print to console and append to the log file (never raises)."""
    line = "%d %s" % (time.ticks_ms(), msg)
    print(line)
    try:
        if os.stat(LOG_PATH)[6] > _MAX_BYTES:
            _rotate()               # a device that runs for days must still be able to report an error on day three
    except OSError:
        pass
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
