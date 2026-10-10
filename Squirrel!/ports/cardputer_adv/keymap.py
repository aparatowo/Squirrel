# keymap.py - the Cardputer ADV keyboard: which action each key gives (read by drivers/tca8418_keypad.py)
#
# Key codes 1..68 are the TCA8418's: row * 10 + column + 1 of the 7 x 8 matrix.

# -----------------------------------------------------------------------------
# FIZYCZNE MAPY KLAWIATURY CARDPUTER (Kody matrycy 1..68)
# -----------------------------------------------------------------------------

# 1. Mapowanie nawigacyjne (MAP_NAV) - używane domyślnie w Menu / Systemie
MAP_NAV = {
    # ROW 1
    1: 'ESC', 5: '1', 11: '2', 15: '3', 21: '4', 25: '5', 31: '6', 35: '7', 41: '8', 45: '9', 51: '0', 55: '-', 61: '=', 65: 'BACKSPACE',
    # ROW 2
    2: 'TAB', 6: 'q', 12: 'w', 16: 'e', 22: 'r', 26: 't', 32: 'y', 36: 'u', 42: 'i', 46: 'o', 52: 'p', 56: '[', 62: ']', 66: '\\',
    # ROW 3
    3: 'FN', 7: 'Aa', 13: 'a', 17: 's', 23: 'd', 27: 'f', 33: 'g', 37: 'h', 43: 'j', 47: 'k', 53: 'l', 57: 'UP', 63: '\'', 67: 'ENTER',
    # ROW 4
    4: 'CTRL', 8: 'OPT', 14: 'ALT', 18: 'z', 24: 'x', 28: 'c', 34: 'v', 38: 'b', 44: 'n', 48: 'm', 54: 'LEFT', 58: 'DOWN', 64: 'RIGHT', 68: 'SPACE'
}

# 2. Mapowanie tekstowe (MAP_TEXT) - domyślne w edytorze (is_text_mode = True)
class KeyMap:
    """A key map = a base map + a few changes on top of it (+ optionally a prefix in front of every action).

    Only .get() is needed by the keypad.  The lookup is done on the fly: building real dicts for CTRL+, OPT+, ALT+ ... would put
    ~220 more strings and 6 more dicts on a heap that is short of room."""
    def __init__(self, base, changes=None, prefix=""):
        self._base, self._changes, self._prefix = base, changes, prefix

    def get(self, code, default=None):
        value = self._changes.get(code) if self._changes is not None else None
        if value is None:
            value = self._base.get(code)
        if value is None:
            return default
        return self._prefix + value if self._prefix else value


MAP_TEXT = KeyMap(MAP_NAV, {
    1: '`',
    57: ';',
    54: ',',
    58: '.',
    64: '/'
})

# 3. Mapowanie po włączeniu FN (MAP_FN) - przywraca nawigację kursorem w edytorze
MAP_FN = KeyMap(MAP_TEXT, {
    1: 'ESC',
    57: 'UP',
    54: 'LEFT',
    58: 'DOWN',
    64: 'RIGHT',
    65: 'DEL'
})

# 4. Mapowanie po włączeniu SHIFT / Aa (MAP_SHIFT)
MAP_SHIFT = {
    # ROW 1
    1: '~', 5: '!', 11: '@', 15: '#', 21: '$', 25: '%', 31: '^', 35: '&', 41: '*', 45: '(', 51: ')', 55: '_', 61: '+', 65: 'DEL',
    # ROW 2
    2: 'TAB', 6: 'Q', 12: 'W', 16: 'E', 22: 'R', 26: 'T', 32: 'Y', 36: 'U', 42: 'I', 46: 'O', 52: 'P', 56: '{', 62: '}', 66: '|',
    # ROW 3
    3: 'FN', 7: 'Aa', 13: 'A', 17: 'S', 23: 'D', 27: 'F', 33: 'G', 37: 'H', 43: 'J', 47: 'K', 53: 'L', 57: ':', 63: '"', 67: 'ENTER',
    # ROW 4
    4: 'CTRL', 8: 'OPT', 14: 'ALT', 18: 'Z', 24: 'X', 28: 'C', 34: 'V', 38: 'B', 44: 'N', 48: 'M', 54: '<', 58: '>', 64: '?', 68: 'SPACE'
}

# 5, 6, 7. Mapy modyfikatorów systemowych
MAP_CTRL = KeyMap(MAP_NAV, prefix="CTRL+")
MAP_OPT  = KeyMap(MAP_TEXT, prefix="OPT+")
MAP_ALT  = KeyMap(MAP_TEXT, prefix="ALT+")
MAP_ALT_SHIFT = KeyMap(MAP_SHIFT, prefix="ALT+")      # ALT with Aa on: ALT+A -> Ą


# -----------------------------------------------------------------------------
# MODIFIER KEY BEHAVIOUR
# -----------------------------------------------------------------------------
# STICKY modifiers remain active until explicitly toggled off (by pressing the
# same modifier key again) OR until a different modifier is activated.
# MOMENTARY modifiers auto-reset after any single non-modifier key is pressed.

MODIFIER_STICKY    = ('SHIFT', 'FN')      # FN and Aa stay on until cancelled
MODIFIER_MOMENTARY = ('CTRL', 'OPT', 'ALT')  # auto-reset after one key use
