# os.py - the device's absolute paths (/sd, /flash, /system) mapped into a host folder
from uos import *
import uos as _o
import sim_state as _s

_ROOTS = ("/sd", "/flash", "/system",
          "/Squirrel", "/apps", "/fonts")                  # plain MicroPython (the watch): the flash is the root
_FILES = ("/boot_log.txt", "/DEV", "/main.py", "/boot.py")


def _p(p):
    if isinstance(p, str):
        if p in _FILES:
            return _s.root + p
        for r in _ROOTS:
            if p == r or p.startswith(r + "/"):
                return _s.root + p
    return p


def stat(p):
    return _o.stat(_p(p))


def listdir(p="."):
    return _o.listdir(_p(p))


def ilistdir(p="."):
    return _o.ilistdir(_p(p))


def mkdir(p):
    return _o.mkdir(_p(p))


def rmdir(p):
    return _o.rmdir(_p(p))


def remove(p):
    return _o.remove(_p(p))


def rename(a, b):
    return _o.rename(_p(a), _p(b))


def statvfs(p):
    return (4096, 4096, 7000000, 6000000, 6000000, 0, 0, 0, 0, 255)


def mount(*a, **k):
    pass


def umount(*a, **k):
    pass


def sync():
    pass
