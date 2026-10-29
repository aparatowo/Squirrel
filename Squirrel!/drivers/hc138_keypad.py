# hc138_keypad.py - a key matrix scanned on GPIOs through a 74HC138 demultiplexer (the classic Cardputer's keyboard)
#
# Three address pins pick one of the 74HC138's eight outputs (Y0..Y7, the one picked is LOW); seven column pins with
# pull-ups read which keys of that line are down (LOW).  8 lines x 7 columns = the 56 keys of the 4 x 14 keyboard.
# A scan gives the same key codes as the TCA8418 of the Cardputer ADV (drivers/tca8418_keypad.py: row * 10 + column
# + 1 of its 7 x 8 matrix), so both keyboards share one key map and everything that turns keys into actions -
# modifiers, text mode, accented letters - is the TCA8418 driver's own.
#
# There is no controller and no interrupt: every call of get_pressed_action() scans the matrix (8 x 7 pin reads).
# A key counts once when it goes down; it has to be up for _RELEASE_SCANS scans in a row before it can count again
# (contact bounce).  Light sleep: acknowledge() leaves the line of _WAKE_LINE picked, so its seven keys pull a column
# LOW - the port lists the column pins among its wake pins (the other keys cannot wake the chip).
import time
from drivers.tca8418_keypad import TCA8418Keypad

_RELEASE_SCANS = 3
# Line i of the 74HC138 and column bit j -> the key's place on the keyboard: lines 0-3 read the odd keyboard columns,
# 4-7 the even ones; keyboard row = 3 - (i % 4), keyboard column = 2 * j (+ 1 for lines 0-3).
_WAKE_LINE = 1                  # keyboard row 2, odd columns: Aa, S, F, H, K, ; (UP), ENTER


def key_code(line, bit):
    """The TCA8418-style code of the key at demultiplexer line `line` (0..7), column input `bit` (0..6)."""
    col = 2 * bit + (1 if line < 4 else 0)          # 0..13, left to right
    row = 3 - (line & 3)                            # 0..3, top to bottom
    return (col >> 1) * 10 + (col & 1) * 4 + row + 1


class HC138Keypad(TCA8418Keypad):
    def __init__(self, line_pins, col_pins, keymap):
        """line_pins: the 74HC138's address pins A0, A1, A2; col_pins: the seven column inputs; keymap: as for
        TCA8418Keypad (the Cardputer's: ports/<port>/keymap.py)."""
        from machine import Pin
        self._init_keys(keymap)
        self._lines = [Pin(p, Pin.OUT) for p in line_pins]
        self._cols = [Pin(p, Pin.IN, Pin.PULL_UP) for p in col_pins]
        self._codes = [[key_code(i, j) for j in range(len(col_pins))] for i in range(8)]
        self._down = {}                 # key code -> scans it has been up since (0 = down now)
        self._queue = []                # key codes pressed, not handed out yet
        self.i2c = None                 # (the TCA8418's attributes, unused here)
        self.addr = None

    def _pick(self, line):
        for n, pin in enumerate(self._lines):
            pin.value((line >> n) & 1)

    def _scan(self):
        """Codes of the keys down right now."""
        down = []
        for i in range(8):
            self._pick(i)
            time.sleep_us(2)                       # let the line settle
            row = self._codes[i]
            for j, pin in enumerate(self._cols):
                if not pin.value():
                    down.append(row[j])
        return down

    def get_pressed_action(self):
        now = self._scan()
        for code in now:
            if code not in self._down:
                self._queue.append(code)            # went down: one event
            self._down[code] = 0
        for code in list(self._down):
            if code not in now:
                self._down[code] += 1
                if self._down[code] >= _RELEASE_SCANS:
                    del self._down[code]            # up long enough: may count again
        if not self._queue:
            self.last_key_code = 0                  # what an empty FIFO does in the TCA8418 driver
            return None, False
        return self._key_event(0x80 | self._queue.pop(0))

    def acknowledge(self):
        """Before a light sleep: pick the line whose keys can wake the chip."""
        self._pick(_WAKE_LINE)
        return True
