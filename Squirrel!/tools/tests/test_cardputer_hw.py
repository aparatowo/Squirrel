# tools/tests/test_cardputer_hw.py - the classic Cardputer's keyboard (drivers/hc138_keypad.py) and the DS3231 clock
# (drivers/ds3231.py) against fakes of their pins and bus (CPython, from the folder with squirrel_app.py)
import os
import sys
import time
import types
sys.path.insert(0, ".")

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


# ---- the two keymaps: the classic Cardputer has its own copy (a port's folder is all its firmware gets) ----
import importlib.util


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adv = load("ports/cardputer_adv/keymap.py", "keymap_adv")
classic = load("ports/cardputer/keymap.py", "keymap_classic")
for name in ("MAP_NAV", "MAP_TEXT", "MAP_FN", "MAP_SHIFT", "MAP_CTRL", "MAP_OPT", "MAP_ALT", "MAP_ALT_SHIFT"):
    a, c = getattr(adv, name), getattr(classic, name)
    check("keymap " + name, all(a.get(code) == c.get(code) for code in range(1, 70)))
check("modifiers", adv.MODIFIER_STICKY == classic.MODIFIER_STICKY and adv.MODIFIER_MOMENTARY == classic.MODIFIER_MOMENTARY)

# ---- the key matrix behind the 74HC138 ----
pressed = set()                     # (line, column bit) of the keys held down


class FakePin:
    OUT, IN, PULL_UP = 1, 2, 3
    lines = {}                      # address pin -> its level

    def __init__(self, number, mode=None, pull=None):
        self.number, self.mode = number, mode

    def value(self, v=None):
        if v is not None:
            FakePin.lines[self.number] = v
            return None
        line = sum(FakePin.lines.get(p, 0) << n for n, p in enumerate((8, 9, 11)))
        bit = (13, 15, 3, 4, 5, 6, 7).index(self.number)
        return 0 if (line, bit) in pressed else 1


sys.modules["machine"] = types.SimpleNamespace(Pin=FakePin)
if not hasattr(time, "sleep_us"):
    time.sleep_us = lambda us: None
from drivers.hc138_keypad import HC138Keypad, key_code

codes = [key_code(i, j) for i in range(8) for j in range(7)]
check("56 different codes", len(set(codes)) == 56)
check("the ADV's codes", set(codes) == set(adv.MAP_NAV))
where = {adv.MAP_NAV[key_code(i, j)]: (i, j) for i in range(8) for j in range(7)}
check("corners", key_code(*where["ESC"]) == 1 and key_code(*where["BACKSPACE"]) == 65 and key_code(*where["SPACE"]) == 68)

kb = HC138Keypad((8, 9, 11), (13, 15, 3, 4, 5, 6, 7), classic)


def poll(n=1):
    out = []
    for _ in range(n):
        action, changed = kb.get_pressed_action()
        if action or changed:
            out.append((action, changed))
    return out


check("nothing down", poll(3) == [])
pressed.add(where["ENTER"])
check("ENTER once", poll(5) == [("ENTER", False)])
pressed.clear()
check("released", poll(5) == [])
pressed.add(where["ENTER"])
check("ENTER again", poll(2) == [("ENTER", False)])
pressed.clear()
poll(1)
pressed.add(where["ENTER"])                       # a bounce: up for one scan only
check("bounce ignored", poll(3) == [])
pressed.clear()
poll(5)
pressed.update((where["UP"], where["DOWN"]))     # two keys in one scan: both, one per call
check("two keys", sorted(a for a, _c in poll(4)) == ["DOWN", "UP"])
pressed.clear()
poll(5)
pressed.add(where["Aa"])                         # a modifier: changes the state, then a letter
check("Aa toggles", poll(2) == [(None, True)])
pressed.clear()
poll(5)
kb.set_text_mode(True)
kb.flags["SHIFT"] = True
pressed.add(where["a"])
check("shift + a", poll(2) == [("A", False)])
pressed.clear()
kb.acknowledge()
check("wake line picked", sum(FakePin.lines.get(p, 0) << n for n, p in enumerate((8, 9, 11))) == 1)

# ---- DS3231 ----


class FakeI2C:
    def __init__(self, present=True):
        self.mem = bytearray(0x13)
        self.present = present

    def readfrom_mem(self, addr, reg, n):
        if not self.present or addr != 0x68:
            raise OSError(19)
        return bytes(self.mem[reg:reg + n])

    def writeto_mem(self, addr, reg, data):
        if not self.present or addr != 0x68:
            raise OSError(19)
        self.mem[reg:reg + len(data)] = data


from drivers.ds3231 import DS3231TimeProvider

try:
    DS3231TimeProvider(FakeI2C(present=False))
    check("absent raises", False)
except OSError:
    pass

bus = FakeI2C()
bus.mem[0x0F] = 0x80                                     # OSF: never set
rtc = DS3231TimeProvider(bus)
check("available", rtc.is_available)
try:
    rtc.read_valid()
    check("OSF refused", False)
except OSError:
    pass
rtc.set_datetime((2026, 10, 18, 23, 59, 30, 6, 0))      # a Sunday
check("OSF cleared", not bus.mem[0x0F] & 0x80)
check("registers", bytes(bus.mem[0:7]) == bytes([0x30, 0x59, 0x23, 0x07, 0x18, 0x10, 0x26]))
check("read back", rtc.read_valid() == (2026, 10, 18, 23, 59, 30, 6, 0))
bus.mem[2] = 0x40 | 0x20 | 0x11                         # 12-hour mode, 11 PM
check("12-hour", rtc.get_datetime()[3] == 23)
bus.mem[2] = 0x40 | 0x12                                 # 12 AM
check("midnight", rtc.get_datetime()[3] == 0)
rtc.set_datetime((2026, 10, 19, 7, 0, 0, 0, 0))
rtc.set_alarm((2026, 10, 19, 7, 30, 0, 0, 0))
check("alarm", bytes(bus.mem[0x0B:0x0E]) == bytes([0x30, 0x07, 0x19]) and bus.mem[0x0E] & 0x06 == 0x06)
bus.mem[0x0F] |= 0x02
check("fired", rtc.alarm_fired())
rtc.clear_alarm_flag()
check("cleared", not rtc.alarm_fired() and bus.mem[0x0E] & 0x02)
rtc.set_alarm(None)
check("disarmed", not bus.mem[0x0E] & 0x02 and bus.mem[0x0E] & 0x04)
bus.mem[0x11], bus.mem[0x12] = 0x19, 0x40               # 25.25 degrees
check("temperature", rtc.temperature() == 25.25)
bus.mem[0x11], bus.mem[0x12] = 0xFF, 0xC0               # -0.25
check("negative temperature", rtc.temperature() == -0.25)

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
