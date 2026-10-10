# boot_log.py - tiny logger that mirrors messages to <flash>/boot_log.txt
#
# <flash> is where the internal flash's file system is mounted: port_config.STORAGE_FLASH_ROOT ("/flash" on the
# Cardputer's UIFlow firmware, "" = the root on plain MicroPython).
#
# After a hardware reset there is no Thonny console, so this file is the only
# way to see what happened during startup.  Each line starts with time.ticks_ms()
# (milliseconds since the chip booted), so the first line of a session also shows
# how long the firmware needed before main.py started.
# Read it with:  print(open('/flash/boot_log.txt').read())
#
# Writing to the flash costs energy and wears it, so only what matters goes to the file:
#   log(msg)    start-up, warnings, errors, things worth finding a day later - console AND file;
#   trace(msg)  routine events (screen changes, CPU speed, memory after a screen load ...) - console only,
#               and the file too in DEV mode (/flash/DEV), where every detail helps.
# The size of the file is kept in memory, so a line costs one append, not an extra os.stat().

import os
import time
from port_config import STORAGE_FLASH_ROOT as _FLASH

LOG_PATH = _FLASH + "/boot_log.txt"
_KEEP_BYTES = 2000   # tail of previous boots kept when the file grows
_MAX_BYTES = 6000    # when the file reaches this, the oldest lines are dropped (the newest _KEEP_BYTES stay): logging never goes silent
_size = None         # bytes in the file as far as we know (None = not known yet: ask os.stat once)
_trace_to_file = False


def _dev_mode():
    try:
        os.stat(_FLASH + "/DEV")
        return True
    except OSError:
        return False


def begin_session():
    """Trim old history (keeping its tail) and mark the start of a boot."""
    global _trace_to_file, _size
    _trace_to_file = _dev_mode()
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
    _size = None
    log("--- boot ---")


def _rotate():
    """Keep the newest _KEEP_BYTES of the log (from a whole line on) and drop the rest."""
    global _size
    _size = None
    try:
        with open(LOG_PATH, "r") as f:
            data = f.read()
        tail = data[-_KEEP_BYTES:]
        nl = tail.find("\n")
        if nl >= 0:
            tail = tail[nl + 1:]
        with open(LOG_PATH, "w") as f:
            f.write(tail)
        _size = len(tail)
    except Exception:
        pass


def log(msg):
    """Print to console and append to the log file (never raises)."""
    global _size
    line = "%d %s\n" % (time.ticks_ms(), msg)
    print(line, end="")
    try:
        if _size is None:
            try:
                _size = os.stat(LOG_PATH)[6]
            except OSError:
                _size = 0
        if _size > _MAX_BYTES:
            _rotate()               # a device that runs for days must still be able to report an error on day three
        with open(LOG_PATH, "a") as f:
            f.write(line)
        _size = (_size or 0) + len(line)
    except Exception:
        pass


def trace(msg):
    """A routine event: to the console, and to the file only in DEV mode."""
    if _trace_to_file:
        log(msg)
    else:
        print("%d %s" % (time.ticks_ms(), msg))
