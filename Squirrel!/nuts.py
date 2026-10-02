# nuts.py - Konfiguracja sprzętowa, kolorystyka oraz stałe dla aplikacji Squirrel
#
# Two kinds of constants live here:
#   * hardware facts (pins, I2C addresses, key maps): fixed, changed only by editing this file;
#   * DEFAULTS of user settings: the ones listed in appconfig_schema.py.  They create
#     /sd/Squirrel/config.txt when it is missing and are what a reset restores; the running
#     program reads the live values through appconfig.cfg, not from here.
from M5 import Lcd

def _get_color(name: str, default_hex: int) -> int:
    return getattr(Lcd, f"COLOR_{name.upper()}", default_hex)

class Colors:
    BLACK       = _get_color("BLACK",       0x000000)
    WHITE       = _get_color("WHITE",       0xFFFFFF)
    RED         = _get_color("RED",         0xFF0000)
    GREEN       = _get_color("GREEN",       0x00FF00)
    BLUE        = _get_color("BLUE",        0x0000FF)
    YELLOW      = _get_color("YELLOW",      0xFFFF00)
    CYAN        = _get_color("CYAN",        0x00FFFF)
    MAGENTA     = _get_color("MAGENTA",     0xFF00FF)
    GRAY        = _get_color("GRAY",        0x808080)
    DARKGRAY    = _get_color("DARKGRAY",    0x444444)
    LIGHTGRAY   = _get_color("LIGHTGRAY",   0xD3D3D3)
    ORANGE      = _get_color("ORANGE",      0xFFA500)
    LIGHTGREEN  = _get_color("LIGHTGREEN",  0x90EE90)

class Fonts:
    FONT_SMALL  = 1
    FONT_MEDIUM = 2
    FONT_LARGE  = 3

# Colours a user can pick by name (config.txt stores the name, not a number).
PALETTE = ("black", "white", "red", "green", "blue", "yellow", "cyan", "magenta",
           "gray", "darkgray", "lightgray", "orange", "lightgreen")

def named_color(name: str) -> int:
    return getattr(Colors, name.upper())

# Default colour names (user settings)
COLOR_BG      = "black"
COLOR_FG      = "orange"
COLOR_ACCENT  = "green"
COLOR_WARNING = "yellow"
COLOR_ERROR   = "red"
# The mark in the corner while typing: "aa" normally, Aa with shift, FN, and OPT / CTRL / ALT.
# "text" = the same colour as the text itself.
COLOR_KEY_NORMAL = "text"
COLOR_KEY_SHIFT  = "blue"
COLOR_KEY_FN     = "cyan"
COLOR_KEY_OPT    = "lightgreen"

# The renderer keeps this dict and updates BG/FG/ACCENT/WARNING/ERROR in place when the
# colour settings change, so every screen picks the new colours up on its next redraw.
THEME = {
    "BG":          named_color(COLOR_BG),
    "FG":          named_color(COLOR_FG),
    "HEADER_BG":   Colors.BLACK,
    "HEADER_FG":   Colors.ORANGE,
    "PANEL_BG":    Colors.DARKGRAY,
    "ACCENT":      named_color(COLOR_ACCENT),
    "SUCCESS":     Colors.GREEN,
    "WARNING":     named_color(COLOR_WARNING),
    "ERROR":       named_color(COLOR_ERROR),
    # marks of the keyboard mode shown while typing; kept in step with the COLOR_KEY_* settings by the renderer
    "KEY_NORMAL":  named_color(COLOR_FG),
    "KEY_SHIFT":   Colors.BLUE,
    "KEY_FN":      Colors.CYAN,
    "KEY_OPT":     Colors.LIGHTGREEN,
}

FONTS_THEME = {
    "CLOCK_DATE":   Fonts.FONT_SMALL,
    "CLOCK_FOOTER": Fonts.FONT_SMALL,
    "MENU_HEADER":  Fonts.FONT_SMALL,
    "MENU_ITEM":    Fonts.FONT_SMALL,
    "ALERT":        Fonts.FONT_SMALL,
}

I2C_ADDR_KEYPAD = 0x34
I2C_SDA_PIN = 8
I2C_SCL_PIN = 9
I2C_FREQ = 400000

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

BASE_DIR = "/sd/Squirrel"

TODO_MAX_CHARS = 160
TODO_TITLE_MAX_LEN = 20

NOTE_TITLE_MAX_LEN = 20
NOTE_BODY_MAX_CHARS = 1000

CLOCK_FOOTER_TEXT = "no need to go nuts"
CLOCK_DATE_OFFSET_X = 0
CLOCK_DATE_OFFSET_Y = 0
CLOCK_TIME_OFFSET_X = -10
CLOCK_TIME_OFFSET_Y = 10
CLOCK_FOOTER_OFFSET_X = 0
CLOCK_FOOTER_OFFSET_Y = 10

VIEW_FOOTER_OFFSET_X = 5
VIEW_FOOTER_OFFSET_Y = 115
# -----------------------------------------------------------------------------
# MODIFIER KEY BEHAVIOUR
# -----------------------------------------------------------------------------
# STICKY modifiers remain active until explicitly toggled off (by pressing the
# same modifier key again) OR until a different modifier is activated.
# MOMENTARY modifiers auto-reset after any single non-modifier key is pressed.

MODIFIER_STICKY    = ('SHIFT', 'FN')      # FN and Aa stay on until cancelled
MODIFIER_MOMENTARY = ('CTRL', 'OPT', 'ALT')  # auto-reset after one key use

# -----------------------------------------------------------------------------
# SD CARD (hardware.SDCard via UIFlow2)
# Cardputer physical SPI pins for the microSD slot
# -----------------------------------------------------------------------------
SD_SLOT  = 3
SD_WIDTH = 1
SD_SCK   = 40
SD_MISO  = 39
SD_MOSI  = 14
SD_CS    = 12
SD_FREQ  = 1000000

# -----------------------------------------------------------------------------
# DS1302 RTC — 3-wire interface pins (all free GPIO on Cardputer)
# -----------------------------------------------------------------------------
RTC_CLK_PIN = 6   # Serial clock
RTC_DAT_PIN = 4   # Bidirectional data
RTC_RST_PIN = 3   # Reset / chip-enable (active HIGH)

# -----------------------------------------------------------------------------
# AUDIO — recording and playback settings
# -----------------------------------------------------------------------------
AUDIO_SAMPLE_RATE = 16000   # Hz — good balance of quality vs file size
AUDIO_BITS        = 16      # bits per sample
AUDIO_STEREO      = False   # mono (SPM1423 is mono)
AUDIO_DEFAULT_VOL = 70      # default playback volume (0-100)

# -----------------------------------------------------------------------------
# DEFAULTS OF USER SETTINGS ADDED WITH THE CONFIG FILE (see appconfig_schema.py)
# -----------------------------------------------------------------------------
CONFIG_FILE     = BASE_DIR + "/config.txt"
CONFIG_POLL_MS  = 3000          # how often the file is checked for outside edits

FOCUS_GOAL_MINUTES = 360        # daily focus goal (6 h)
FOCUS_DOT = True                # coloured dot in the corner of screens while the focus timer runs (never on the clock)

TIMESYNC_AT_BOOT    = True      # one Wi-Fi/NTP attempt at start-up when no DS1302 time
TIME_UTC_OFFSET_MIN = 60        # standard time offset from UTC (Poland: +60)
TIME_EU_DST         = True      # European summer time

AUDIO_MIC_MAGNIFICATION = 128   # microphone gain; 0 = leave the firmware default

WIFI_SSID     = ""              # fallback network, used when UIFlow has none saved
WIFI_PASSWORD = ""

# ---- Status bars made of '#' characters (battery, focus progress) ----
BARS_CLOCK = True               # vertical bars at the sides of the clock
BARS_MENU = False               # turn the '#' lines above and below menu titles into the same bars
BARS_OFFSET_X = 0               # distance of the vertical bars from the screen edges (pixels)
BARS_OFFSET_Y = 0               # shift of the vertical bars downwards (pixels)
BATTERY_BLUE_PCT = 80           # battery at or above: blue tail; below: green ...
BATTERY_GREEN_PCT = 50          # ... at or above this: green; below: yellow ...
BATTERY_YELLOW_PCT = 20         # ... at or above this: yellow; below: red
FOCUS_RED_PCT = 25              # daily focus progress below this: red
FOCUS_YELLOW_PCT = 60           # below this: yellow; then green; at 100 (goal reached): blue

# ---- Screen ----
SCREEN_DIM_SECONDS = 30         # idle time before the screen dims; 0 = never
BRIGHTNESS = 0                  # normal brightness 1-255; 0 = leave whatever the device starts with
DIM_BRIGHTNESS = 0              # brightness while dimmed, in percent of the normal one (0 = off)

# ---- Notifications ----
NOTIFY_SOUND = True
NOTIFY_VOLUME = 60              # percent

WIFI_PROFILES_FILE = BASE_DIR + "/wifi.json"    # the WiFi networks saved from Settings -> WiFi networks

# ---- Language ----
KEYBOARD_LAYOUT = "pl"          # ALT + letter types an accented one: "pl" (ALT+a = ą), "de" (ALT+a = ä), "en" (off)
FONT_ENABLED = False            # draw with the .vlw font (Polish letters).  Switch it on from Settings -> Experimental -> Font test
# The font is read by the firmware as a FILE, so it cannot be frozen into it: it stays on the device.
# /flash/fonts/ is the place for a frozen build (no /flash/apps/ folder is needed any more).
FONT_FILES = ("/flash/fonts/squirrel.vlw", "/flash/apps/Squirrel/fonts/squirrel.vlw", "/sd/Squirrel/fonts/squirrel.vlw")

# ---- Notes and To-Do ----
MIND_DUMP_MAX_CHARS = 200       # a quick thought: ENTER saves it
TODO_KEEP_DAYS = 7              # a To-Do marked as done is deleted this many days later

# ---- Routines, Pomodoro ----
ROUTINE_SNOOZE_MIN = 10         # no reaction to a routine for 30 s = it comes back after this many minutes
ROUTINE_MAX_SNOOZES = 6         # ... at most this many times (OPT or DEL ends it earlier)
POMODORO_WORK_MIN = 25
POMODORO_BREAK_MIN = 5
POMODORO_LONG_BREAK_MIN = 15    # after the last work block of a round
POMODORO_CYCLES = 4             # work blocks in one round
TRAINING_FILE = BASE_DIR + "/training.json"
ROUTINES_FILE = BASE_DIR + "/routines.json"
MAX_BLOCK_SECONDS = 90 * 60     # the longest block of a training

# ---- Cuckoo clock, metronome ----
CUCKOO_ENABLED = False
CUCKOO_QUARTERS = True          # a quiet tick every 15 minutes (the cuckoo itself is on the hour)
CUCKOO_QUARTER_VOLUME = 20      # percent
METRO_INTERVAL_S = 5            # 1, 2, 5, 30, 60 or 120 seconds
METRO_VOLUME = 50               # percent

# ---- Power ----
BATTERY_LOG = False             # a line every 10 minutes in /sd/Squirrel/battery.csv, to measure the drain of each power mode
POWER_SAVE = True               # slower CPU and a longer pause between loop passes while the screen is dimmed
POWER_LIGHT_SLEEP = False       # experimental: light sleep while the screen is dimmed (the USB console drops)
POWER_UNLOAD_SCREENS = True     # a rarely used screen is removed from memory when you leave it (more free heap, slower to open again)
