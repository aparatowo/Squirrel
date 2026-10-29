# keymap.py - the Cardputer ADV keyboard: which action each key gives (read by drivers/tca8418_keypad.py)
#
# Key codes 1..68 are the TCA8418's: row * 10 + column + 1 of the 7 x 8 matrix.

# -----------------------------------------------------------------------------
# FIZYCZNE MAPY KLAWIATURY CARDPUTER (Kody matrycy 1..68)
# -----------------------------------------------------------------------------

class Codes:
    """key code -> action, kept as a tuple indexed by the code (None where there is no key).  Frozen into the
    firmware a tuple of constants stays in flash; a dict of 56 keys would be built in RAM (about 1 KB each)."""
    def __init__(self, actions):
        self._a = actions

    def get(self, code, default=None):
        a = self._a
        value = a[code] if 0 <= code < len(a) else None
        return default if value is None else value

    def __getitem__(self, code):
        value = self.get(code)
        if value is None:
            raise KeyError(code)
        return value

    def __iter__(self):
        """The codes that have a key."""
        return (code for code, value in enumerate(self._a) if value is not None)


# 1. Navigation (MAP_NAV) - the default in the menus and the system screens
MAP_NAV = Codes((
    None, 'ESC', 'TAB', 'FN', 'CTRL', '1', 'q', 'Aa', 'OPT', None,  # 0-9
    None, '2', 'w', 'a', 'ALT', '3', 'e', 's', 'z', None,  # 10-19
    None, '4', 'r', 'd', 'x', '5', 't', 'f', 'c', None,  # 20-29
    None, '6', 'y', 'g', 'v', '7', 'u', 'h', 'b', None,  # 30-39
    None, '8', 'i', 'j', 'n', '9', 'o', 'k', 'm', None,  # 40-49
    None, '0', 'p', 'l', 'LEFT', '-', '[', 'UP', 'DOWN', None,  # 50-59
    None, '=', ']', "'", 'RIGHT', 'BACKSPACE', '\\', 'ENTER', 'SPACE',  # 60-68
))

# 2. Text (MAP_TEXT) - the default in an editor (is_text_mode = True)
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

# 3. With FN (MAP_FN) - brings back the cursor keys in an editor
MAP_FN = KeyMap(MAP_TEXT, {
    1: 'ESC',
    57: 'UP',
    54: 'LEFT',
    58: 'DOWN',
    64: 'RIGHT',
    65: 'DEL'
})

# 4. With SHIFT / Aa (MAP_SHIFT)
MAP_SHIFT = Codes((
    None, '~', 'TAB', 'FN', 'CTRL', '!', 'Q', 'Aa', 'OPT', None,  # 0-9
    None, '@', 'W', 'A', 'ALT', '#', 'E', 'S', 'Z', None,  # 10-19
    None, '$', 'R', 'D', 'X', '%', 'T', 'F', 'C', None,  # 20-29
    None, '^', 'Y', 'G', 'V', '&', 'U', 'H', 'B', None,  # 30-39
    None, '*', 'I', 'J', 'N', '(', 'O', 'K', 'M', None,  # 40-49
    None, ')', 'P', 'L', '<', '_', '{', ':', '>', None,  # 50-59
    None, '+', '}', '"', '?', 'BACKSPACE', '|', 'ENTER', 'SPACE',  # 60-68 (Backspace stays one: Aa is on while typing
                                                                    # capitals, and FN - the way to DEL - turns Aa off)
))

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
