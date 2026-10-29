# appconfig_schema.py - which settings exist, and what values each one accepts
#
# One row per user setting:  (key, kind, group, label, extra)
#   kind "int"    extra = (min, max, step)   typed value, out-of-range input is clamped
#   kind "bool"   extra = None               true / false
#   kind "choice" extra = tuple of options   pick from the list
#   kind "color"  extra = None               a name from nuts.PALETTE
#   kind "text"   extra = max length         free text
#   kind "secret" extra = max length         free text that must not be shown on screen
#   kind "time"   extra = None               a time of day: minutes after midnight, HH:MM in the file
#   kind "days"   extra = None               days of the week: bit 0 = Monday, MTWTFSS in the file ('.' = off)
# The default of every key is the same-named constant in nuts.py.  Labels are at most 18 characters: Personalize lists
# a label and its value on one row.  Anything a user needs to know beyond the name (the unit, what 0 means, when it
# takes effect) goes into HELP below: it is shown once the setting is opened, and as a comment in config.txt.

# The buzzer modes (buzzer.MODE_NAMES, with "auto" = the feature's own choice in front) and the LED modes
# (led.MODE_NAMES, with "off" in front); kept here so the schema needs no import of buzzer.py / led.py
BUZZER_MODES = ("auto", "click", "short", "double", "triple", "long", "alarm", "sos")
MODES = ("off", "flash", "double", "triple", "long", "pulse", "alarm", "sos")

# "deep" only where the device can wake from a deep sleep by a clock alarm (features.toml: deep_sleep); "light" unless
# the port turns it off ([power_mgmt] light_sleep = false: the Cardputer ADV, see docs/implementation/*/backlog.md)
from features import has as _has
import port_config as _port
SLEEP_MODES = (("off",) + (("light",) if getattr(_port, "POWER_MGMT_LIGHT_SLEEP", True) else ())
               + (("deep",) if _has("deep_sleep") else ()))
# Without a deep sleep the sleep mode is light sleep alone, and that is experimental there (the first Cardputer); with
# no light sleep either there is nothing to choose: the setting stays (the code reads it), out of sight ("Hidden")
_SLEEP_GROUP = "Power" if _has("deep_sleep") else ("Experimental" if len(SLEEP_MODES) > 1 else "Hidden")

# The clock modules this device can take ([clock.<chip>] sections of its port.toml); "off" = none plugged in
CLOCK_MODULES = ("off",) + tuple(c for c in ("ds3231", "ds1302") if hasattr(_port, "CLOCK_%s_DRIVER" % c.upper()))

SETTINGS = (
    # ---- Display ----
    ("COLOR_FG",      "color", "Display", "Main colour", None),
    ("COLOR_ACCENT",  "color", "Display", "Accent colour", None),
    ("COLOR_WARNING", "color", "Display", "Warning colour", None),
    ("COLOR_ERROR",   "color", "Display", "Error colour", None),
    ("COLOR_BG",      "color", "Display", "Background colour", None),
    ("LANGUAGE",      "choice", "Display", "Language", ("en", "pl", "fr", "de")),
    ("FONT_ENABLED",  "bool",  "Display", "Use font", None),
    ("CLOCK_FOOTER_TEXT",     "text", "Display", "Clock footer text", 30),
    ("CLOCK_DATE_OFFSET_X",   "int", "Display", "Clock date X", (-40, 40, 1)),
    ("CLOCK_DATE_OFFSET_Y",   "int", "Display", "Clock date Y", (-40, 40, 1)),
    ("CLOCK_TIME_OFFSET_X",   "int", "Display", "Clock time X", (-60, 60, 1)),
    ("CLOCK_TIME_OFFSET_Y",   "int", "Display", "Clock time Y", (-40, 40, 1)),
    ("CLOCK_ONE_OFFSET_X",    "int", "Display", "Clock 1x:xx X", (-30, 30, 1)),
    ("CLOCK_FOOTER_OFFSET_X", "int", "Display", "Clock footer X", (-60, 60, 1)),
    ("CLOCK_FOOTER_OFFSET_Y", "int", "Display", "Clock footer Y", (-40, 40, 1)),
    ("VIEW_FOOTER_OFFSET_X",  "int", "Display", "Viewer footer X", (-20, 60, 1)),
    ("VIEW_FOOTER_OFFSET_Y",  "int", "Display", "Viewer footer Y", (90, 130, 1)),
    # ---- Notes and To-Do ----
    ("TODO_MAX_CHARS",      "int", "Notes", "To-Do max length", (20, 500, 10)),
    ("TODO_TITLE_MAX_LEN",  "int", "Notes", "To-Do title length", (8, 30, 1)),
    ("NOTE_TITLE_MAX_LEN",  "int", "Notes", "Note title length", (8, 40, 1)),
    ("NOTE_BODY_MAX_CHARS", "int", "Notes", "Note max length", (100, 2000, 50)),
    ("MIND_DUMP_MAX_CHARS", "int", "Notes", "Mind dump length", (50, 500, 10)),
    ("TODO_KEEP_DAYS",      "int", "Notes", "Keep done To-Dos", (1, 60, 1)),
    # ---- Focus ----
    ("FOCUS_GOAL_MINUTES", "int", "Focus", "Daily focus goal", (10, 720, 10)),
    ("FOCUS_UNDO_MIN",     "int", "Focus", "Take back minutes", (5, 60, 5)),
    ("ROUTINE_SNOOZE_MIN",  "int", "Focus", "Routine snooze", (1, 60, 1)),
    ("POMODORO_WORK_MIN",   "int", "Focus", "Pomodoro work", (1, 90, 1)),
    ("POMODORO_BREAK_MIN",  "int", "Focus", "Pomodoro break", (1, 30, 1)),
    ("POMODORO_LONG_BREAK_MIN", "int", "Focus", "Long break", (1, 60, 1)),
    ("POMODORO_CYCLES",     "int", "Focus", "Pomodoro blocks", (1, 8, 1)),
    ("HOURGLASS_MIN",       "int", "Focus", "Hourglass minutes", (1, 240, 1)),
    ("FOCUS_DOT", "bool", "Focus", "Focus dot", None),
    # ---- Keyboard ----
    ("KEYBOARD_LAYOUT",  "choice", "Keyboard", "ALT+letter layout", ("pl", "en", "de")),
    ("COLOR_KEY_NORMAL", "choice", "Keyboard", "Mark: aa (normal)", ("text", "black", "white", "red", "green", "blue", "yellow", "cyan", "magenta", "gray", "darkgray", "lightgray", "orange", "lightgreen")),
    ("COLOR_KEY_SHIFT",  "color",  "Keyboard", "Mark: Aa (shift)", None),
    ("COLOR_KEY_FN",     "color",  "Keyboard", "Mark: FN", None),
    ("COLOR_KEY_OPT",    "color",  "Keyboard", "Mark: OPT/CTRL/ALT", None),
    # ---- Status bars ----
    ("BARS_CLOCK",         "bool", "Bars", "Bars on clock", None),
    ("BARS_MENU",          "bool", "Bars", "Bars in menus", None),
    ("BARS_OFFSET_X",      "int",  "Bars", "Bars from edge", (0, 60, 1)),
    ("BARS_OFFSET_Y",      "int",  "Bars", "Bars shift down", (0, 20, 1)),
    ("BARS_TOP",           "choice", "Bars", "Top bar", ("hourglass", "hour", "full", "off")),
    ("BARS_TOP_COLOR",     "color", "Bars", "Top bar colour", None),
    ("BARS_BOTTOM",        "choice", "Bars", "Bottom bar", ("quarter", "full", "off")),
    ("BARS_BOTTOM_COLOR",  "color", "Bars", "Bottom bar colour", None),
    ("BARS_CHARGING",      "bool",  "Bars", "Charging mark", None),
    ("FOCUS_BAR_FROM",     "choice", "Bars", "Focus bar from", ("bottom", "top")),
    ("BATTERY_BLUE_PCT",   "int",  "Bars", "Battery: blue", (30, 100, 5)),
    ("BATTERY_GREEN_PCT",  "int",  "Bars", "Battery: green", (10, 95, 5)),
    ("BATTERY_YELLOW_PCT", "int",  "Bars", "Battery: yellow", (5, 90, 5)),
    ("FOCUS_RED_PCT",      "int",  "Bars", "Focus: red", (5, 95, 5)),
    ("FOCUS_YELLOW_PCT",   "int",  "Bars", "Focus: yellow", (10, 99, 5)),
    # ---- Screen ----
    ("SCREEN_DIM_CLOCK_SECONDS", "int", "Screen", "Dim clock after", (0, 600, 5)),
    ("SCREEN_DIM_OTHER_SECONDS", "int", "Screen", "Dim others after", (0, 600, 5)),
    ("BRIGHTNESS",         "int", "Screen", "Brightness", (0, 255, 5)),
    ("DIM_BRIGHTNESS",     "int", "Screen", "Dimmed brightness", (0, 100, 5)),
    # ---- Time ----
    ("TIMESYNC_AT_BOOT",    "bool", "Time", "WiFi sync at start", None),
    ("TIME_UTC_OFFSET_MIN", "int",  "Time", "UTC offset", (-720, 840, 30)),
    ("TIME_EU_DST",         "bool", "Time", "EU summer time", None),
    ("RTC_CHIP",            "choice", "Time", "Clock module", CLOCK_MODULES),
    # ---- Audio ----
    ("AUDIO_MIC_MAGNIFICATION", "choice", "Audio", "Microphone gain", (0, 16, 32, 64, 96, 128, 160, 192, 255)),
    ("AUDIO_DEFAULT_VOL",       "int",    "Audio", "Playback volume", (0, 100, 10)),
    ("NOTIFY_SOUND",            "bool",   "Audio", "Notification sound", None),
    ("NOTIFY_VOLUME",           "int",    "Audio", "Notify volume", (0, 100, 10)),
    ("METRO_INTERVAL_S",        "choice", "Audio", "Metronome interval", (0.125, 0.25, 0.5, 1, 2, 5, 30, 60, 120)),
    ("METRO_VOLUME",            "int",    "Audio", "Metronome volume", (0, 100, 10)),
    ("METRO_SOUND",             "choice", "Audio", "Metronome sound", ("tone", "click")),
    # ---- Network ----
    ("WIFI_SSID",     "text",   "Network", "Fallback WiFi name", 32),
    ("WIFI_PASSWORD", "secret", "Network", "Fallback password", 63),
    # ---- Cuckoo (reached from Focus tools -> Cuckoo clock) ----
    ("CUCKOO_ENABLED",        "bool", "Cuckoo", "Cuckoo", None),
    ("CUCKOO_QUARTERS",       "bool", "Cuckoo", "Quarters", None),
    ("CUCKOO_QUARTER_VOLUME", "int",  "Cuckoo", "Volume", (0, 100, 10)),
    # ---- Buzzer (Personalize, with its status; tests in Settings -> Experimental) ----
    ("BUZZER_NOTIFY",         "bool",   "Buzzer", "Notifications", None),
    ("BUZZER_NOTIFY_MODE",    "choice", "Buzzer", "Notify: mode", BUZZER_MODES),
    ("BUZZER_INTERVALS",      "bool",   "Buzzer", "Pomodoro/Training", None),
    ("BUZZER_INTERVALS_MODE", "choice", "Buzzer", "Pomodoro: mode", BUZZER_MODES),
    ("BUZZER_METRONOME",      "bool",   "Buzzer", "Metronome", None),
    ("BUZZER_METRONOME_MODE", "choice", "Buzzer", "Metronome: mode", BUZZER_MODES),
    ("BUZZER_CUCKOO",         "bool",   "Buzzer", "Cuckoo", None),
    ("BUZZER_CUCKOO_MODE",    "choice", "Buzzer", "Cuckoo: mode", BUZZER_MODES),
    ("BUZZER_HOURGLASS",      "bool",   "Buzzer", "Hourglass", None),
    ("BUZZER_HOURGLASS_MODE", "choice", "Buzzer", "Hourglass: mode", BUZZER_MODES),
    ("BUZZER_BATTERY",        "bool",   "Buzzer", "Low battery", None),
    ("BUZZER_BATTERY_MODE",   "choice", "Buzzer", "Battery: mode", BUZZER_MODES),
    # ---- LED (in Personalize, with its status; tests in Settings -> Experimental) ----
    ("LED_BRIGHTNESS",      "int",    "LED", "LED brightness", (1, 100, 5)),
    ("LED_NOTIFY",          "choice", "LED", "Notify: blink", MODES),
    ("LED_NOTIFY_COLOR",    "color",  "LED", "Notify: colour", None),
    ("LED_INTERVALS",       "choice", "LED", "Pomodoro: blink", MODES),
    ("LED_INTERVALS_COLOR", "color",  "LED", "Pomodoro: colour", None),
    ("LED_METRONOME",       "choice", "LED", "Metronome: blink", MODES),
    ("LED_METRONOME_COLOR", "color",  "LED", "Metronome: colour", None),
    ("LED_CUCKOO",          "choice", "LED", "Cuckoo: blink", MODES),
    ("LED_CUCKOO_COLOR",    "color",  "LED", "Cuckoo: colour", None),
    ("LED_HOURGLASS",       "choice", "LED", "Hourglass: blink", MODES),
    ("LED_HOURGLASS_COLOR", "color",  "LED", "Hourglass: colour", None),
    ("LED_BREATHING",       "bool",   "LED", "Breathing light", None),
    ("LED_BATTERY",         "choice", "LED", "Battery: blink", MODES),
    ("LED_BATTERY_COLOR",   "color",  "LED", "Battery: colour", None),
    # ---- Silent mode (reached from Settings -> Silent mode; see quiet_hours.py) ----
    ("QUIET_SOUND_FROM",  "time", "Silent", "Sound quiet from", None),
    ("QUIET_SOUND_TO",    "time", "Silent", "Sound quiet until", None),
    ("QUIET_SOUND_DAYS",  "days", "Silent", "Sound quiet days", None),
    ("QUIET_BUZZER_FROM", "time", "Silent", "Buzzer quiet from", None),
    ("QUIET_BUZZER_TO",   "time", "Silent", "Buzzer quiet until", None),
    ("QUIET_BUZZER_DAYS", "days", "Silent", "Buzzer quiet days", None),
    ("QUIET_LED_FROM",    "time", "Silent", "LED quiet from", None),
    ("QUIET_LED_TO",      "time", "Silent", "LED quiet until", None),
    ("QUIET_LED_DAYS",    "days", "Silent", "LED quiet days", None),
    # ---- Power ----
    ("POWER_SAVE",        "bool", "Power", "Power save", None),
    ("BATTERY_LOG",       "bool", "Power", "Battery log", None),
    ("BATTERY_WARN",      "bool", "Power", "Battery warnings", None),
    ("BATTERY_WARN_SOUND", "bool", "Power", "Warning sound", None),
    ("POWER_SLEEP",       "choice", _SLEEP_GROUP, "Sleep mode", SLEEP_MODES),
    ("POWER_DEEP_SLEEP_MIN", "int", "Power", "Deep sleep after", (1, 120, 1)),
    ("POWER_UNLOAD_SCREENS", "bool", "Power", "Free screens", None),
    # ---- Experimental (Settings -> Experimental -> Settings) ----
    ("CHARGE_GUESS",      "bool", "Experimental", "Charge detection", None),
    # ---- Bluetooth ----
    ("BLE_AUTO_SYNC_MIN", "int", "Bluetooth", "Auto sync every", (0, 240, 15)),
)

# Shown when a setting is opened in Personalize (and as a comment in config.txt).  At most 38 characters per line; a
# second line after "\n" is shown on the screens that have room for it.  Pairs (key, text) in one flat tuple, not a
# dict: frozen into the firmware a tuple of constants stays in flash, a dict is built in RAM (help_of() finds a key by
# a plain search - asked only when a setting is opened or config.txt is written).
HELP = (
    "FONT_ENABLED",           "Polish letters. Takes effect after\na restart (hold G0 at start to skip).",
    "CLOCK_DATE_OFFSET_X",    "Pixels; more = to the right",
    "CLOCK_DATE_OFFSET_Y",    "Pixels; more = lower",
    "CLOCK_TIME_OFFSET_X",    "Pixels; more = to the right",
    "CLOCK_TIME_OFFSET_Y",    "Pixels; more = lower",
    "CLOCK_ONE_OFFSET_X",     "Pixels for 10:00 - 19:59, whose '1'\nis only its right side; minus = left,\n0 = off",
    "CLOCK_FOOTER_OFFSET_X",  "Pixels; more = to the right",
    "CLOCK_FOOTER_OFFSET_Y",  "Pixels; more = lower",
    "VIEW_FOOTER_OFFSET_X",   "Note viewer footer. Pixels;\nmore = to the right",
    "VIEW_FOOTER_OFFSET_Y",   "Note viewer footer. Pixels;\nmore = lower",
    "TODO_MAX_CHARS",         "Characters in one To-Do",
    "TODO_TITLE_MAX_LEN",     "Characters in a To-Do title",
    "NOTE_TITLE_MAX_LEN",     "Characters in a note title",
    "NOTE_BODY_MAX_CHARS",    "Characters in one note",
    "MIND_DUMP_MAX_CHARS",    "Characters in one thought",
    "TODO_KEEP_DAYS",         "Days a done To-Do stays, then it goes",
    "FOCUS_GOAL_MINUTES",     "Minutes of focus a day",
    "FOCUS_UNDO_MIN",         "Minutes taken back from today's focus\nafter a distraction (Statistics: -)",
    "ROUTINE_SNOOZE_MIN",     "Minutes before an unanswered\nroutine comes back",
    "POMODORO_WORK_MIN",      "Minutes of one work block",
    "POMODORO_BREAK_MIN",     "Minutes of a short break",
    "POMODORO_LONG_BREAK_MIN", "Minutes; after the last block\nof a round",
    "POMODORO_CYCLES",        "Work blocks in one round",
    "HOURGLASS_MIN",          "Minutes the hourglass is set to;\nits screen changes it too",
    "FOCUS_DOT",              "Dot in the corner while the focus\ntimer runs (never on the clock)",
    "COLOR_KEY_NORMAL",       "text = the colour of the text",
    "BARS_CLOCK",             "Battery and focus bars on the clock",
    "BARS_MENU",              "Lines above and below menu titles\nbecome battery and focus bars",
    "BARS_OFFSET_X",          "Pixels from the screen edges",
    "BARS_OFFSET_Y",          "Pixels down",
    "BARS_TOP",               "On the clock. hourglass: its progress\n(the hour while it is not set); hour:\nthe hour going by; full: a plain bar",
    "BARS_TOP_COLOR",         "The colour of the time gone by",
    "BARS_BOTTOM",            "On the clock. quarter: the quarter\nhour going by, from the right; full:\na plain bar",
    "BARS_BOTTOM_COLOR",      "The colour of the time gone by",
    "FOCUS_BAR_FROM",         "The clock's focus bar fills from the\nbottom, or from the top (classic)",
    "BATTERY_BLUE_PCT",       "Battery % from which the bar is blue",
    "BATTERY_GREEN_PCT",      "Battery % from which it is green",
    "BATTERY_YELLOW_PCT",     "Battery % from which it is yellow;\nbelow: red",
    "FOCUS_RED_PCT",          "Goal % below which the bar is red",
    "FOCUS_YELLOW_PCT",       "Goal % below which it is yellow;\nthen green, blue at 100",
    "SCREEN_DIM_CLOCK_SECONDS", "Seconds without a key; 0 = never",
    "SCREEN_DIM_OTHER_SECONDS", "Seconds without a key; 0 = never",
    "BRIGHTNESS",             "1-255; 0 = as the device starts",
    "DIM_BRIGHTNESS",         "% of normal brightness; 0 = off",
    "TIMESYNC_AT_BOOT",       "Set the clock over WiFi at start\nwhen there is no clock module",
    "RTC_CHIP",               "The clock module plugged in (it keeps\nthe time while the power is off);\noff = none: its code is not loaded",
    "TIME_UTC_OFFSET_MIN",    "Minutes; Poland: 60 (summer time\nis added by EU summer time)",
    "AUDIO_MIC_MAGNIFICATION", "0 = the firmware default",
    "AUDIO_DEFAULT_VOL",      "% for voice notes",
    "NOTIFY_VOLUME",          "% for notification sounds",
    "METRO_INTERVAL_S",       "Seconds between beats; 0.125 = 1/8 s,\n0.25 = 1/4 s, 0.5 = 1/2 s",
    "METRO_VOLUME",           "% for the metronome",
    "METRO_SOUND",            "tone: a short beep; click: a dry\nclick, like a clock's (S on the\nmetronome's screen)",
    "WIFI_SSID",              "Used when no saved network is in range",
    "WIFI_PASSWORD",          "Of the fallback network (hidden)",
    "CUCKOO_QUARTERS",        "A quiet tick every 15 minutes",
    "CUCKOO_QUARTER_VOLUME",  "% for the quarter tick",
    "BUZZER_NOTIFY_MODE",     "auto = the feature's own signal",
    "BUZZER_INTERVALS_MODE",  "auto = double, triple (hard block),\nlong (break)",
    "BUZZER_METRONOME_MODE",  "auto = a click on every beat",
    "BUZZER_CUCKOO_MODE",     "auto = double on the hour, click\nfor the quarters",
    "BUZZER_HOURGLASS",       "When the hourglass runs out (also in\nthe silent hours: it was set by hand)",
    "BUZZER_HOURGLASS_MODE",  "auto = alarm",
    "LED_BRIGHTNESS",         "% of full brightness; bright colours\nare limited by LED_MAX_SUM (nuts.py)",
    "LED_BATTERY",            "With the low-battery warnings\n(Power -> Battery warnings)",
    "BARS_CHARGING",          "A lightning mark by the battery bar\nwhile it charges (Cardputer: needs\nCharge detection, Experimental)",
    "BATTERY_WARN",           "A warning at 15%, 10%, 5% and\nright before the battery runs out",
    "BATTERY_WARN_SOUND",     "The warning with a sound (the buzzer:\nBuzzer -> Low battery)",
    "BUZZER_BATTERY_MODE",    "auto = double; alarm when it is\nalmost empty",
    "CHARGE_GUESS",           "Guess charging from the battery's\nvoltage (and a computer on the USB):\nthe device cannot tell. Experimental",
    "LED_BREATHING",          "Green breathing in, blue out",
    "POWER_SAVE",             "Slower CPU while the screen is dimmed",
    "BATTERY_LOG",            "Energy data every 10 min: battery.csv\non the SD card; never sent anywhere",
    "LANGUAGE",               "The language of every screen.\nAny but English turns the font on\n(for the accented letters)",
    "BLE_AUTO_SYNC_MIN",      "Minutes; 0 = only on demand. On the\nclock (every 60: at full hours). The\nwatch wakes for it: each sync costs\nabout 1 mAh of its battery",
    "POWER_SLEEP",            ("light: sleeps while dimmed (the USB\nconsole disconnects); deep: after the\ntime below; the button / alarms wake"
                               if _has("deep_sleep") else
                               "light: sleeps while dimmed. The USB\nconsole drops; after a sound the\nspeaker ticks faintly (by the ear)"),
    "POWER_DEEP_SLEEP_MIN",   "Minutes dimmed before a deep sleep\n(not while Pomodoro / metronome run)",
    "POWER_UNLOAD_SCREENS",   "Rarely used screens leave memory\n(more free heap, slower to open)",
)


def help_of(key):
    """The help text of setting `key`, or ""."""
    for i in range(0, len(HELP), 2):
        if HELP[i] == key:
            return HELP[i + 1]
    return ""
