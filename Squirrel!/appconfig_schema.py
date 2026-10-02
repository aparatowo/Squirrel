# appconfig_schema.py - which settings exist, and what values each one accepts
#
# One row per user setting:  (key, kind, group, label, extra)
#   kind "int"    extra = (min, max, step)   typed value, out-of-range input is clamped
#   kind "bool"   extra = None               true / false
#   kind "choice" extra = tuple of options   pick from the list
#   kind "color"  extra = None               a name from nuts.PALETTE
#   kind "text"   extra = max length         free text
#   kind "secret" extra = max length         free text that must not be shown on screen
# The default of every key is the same-named constant in nuts.py.  Labels stay short
# (<= 26 characters) because they are shown in the menu.

SETTINGS = (
    # ---- Display ----
    ("COLOR_FG",      "color", "Display", "Main colour", None),
    ("COLOR_ACCENT",  "color", "Display", "Accent colour", None),
    ("COLOR_WARNING", "color", "Display", "Warning colour", None),
    ("COLOR_ERROR",   "color", "Display", "Error colour", None),
    ("COLOR_BG",      "color", "Display", "Background colour", None),
    ("FONT_ENABLED",  "bool",  "Display", "Use font (restart)", None),
    ("CLOCK_FOOTER_TEXT",     "text", "Display", "Clock footer text", 30),
    ("CLOCK_DATE_OFFSET_X",   "int", "Display", "Clock date shift X", (-40, 40, 1)),
    ("CLOCK_DATE_OFFSET_Y",   "int", "Display", "Clock date shift Y", (-40, 40, 1)),
    ("CLOCK_TIME_OFFSET_X",   "int", "Display", "Clock digits shift X", (-60, 60, 1)),
    ("CLOCK_TIME_OFFSET_Y",   "int", "Display", "Clock digits shift Y", (-40, 40, 1)),
    ("CLOCK_FOOTER_OFFSET_X", "int", "Display", "Clock footer shift X", (-60, 60, 1)),
    ("CLOCK_FOOTER_OFFSET_Y", "int", "Display", "Clock footer shift Y", (-40, 40, 1)),
    ("VIEW_FOOTER_OFFSET_X",  "int", "Display", "Viewer footer shift X", (-20, 60, 1)),
    ("VIEW_FOOTER_OFFSET_Y",  "int", "Display", "Viewer footer shift Y", (90, 130, 1)),
    # ---- Notes and To-Do ----
    ("TODO_MAX_CHARS",      "int", "Notes", "To-Do max characters", (20, 500, 10)),
    ("TODO_TITLE_MAX_LEN",  "int", "Notes", "To-Do title length", (8, 30, 1)),
    ("NOTE_TITLE_MAX_LEN",  "int", "Notes", "Note title length", (8, 40, 1)),
    ("NOTE_BODY_MAX_CHARS", "int", "Notes", "Note max characters", (100, 2000, 50)),
    ("MIND_DUMP_MAX_CHARS", "int", "Notes", "Mind Dump max characters", (50, 500, 10)),
    ("TODO_KEEP_DAYS",      "int", "Notes", "Keep done To-Dos (days)", (1, 60, 1)),
    # ---- Focus ----
    ("FOCUS_GOAL_MINUTES", "int", "Focus", "Daily focus goal (min)", (10, 720, 10)),
    ("ROUTINE_SNOOZE_MIN",  "int", "Focus", "Routine snooze (min)", (1, 60, 1)),
    ("POMODORO_WORK_MIN",   "int", "Focus", "Pomodoro work (min)", (1, 90, 1)),
    ("POMODORO_BREAK_MIN",  "int", "Focus", "Pomodoro break (min)", (1, 30, 1)),
    ("POMODORO_LONG_BREAK_MIN", "int", "Focus", "Pomodoro long break", (1, 60, 1)),
    ("POMODORO_CYCLES",     "int", "Focus", "Pomodoro work blocks", (1, 8, 1)),
    ("FOCUS_DOT", "bool", "Focus", "Focus dot on screens", None),
    # ---- Keyboard ----
    ("KEYBOARD_LAYOUT",  "choice", "Keyboard", "ALT+letter layout", ("pl", "en", "de")),
    ("COLOR_KEY_NORMAL", "choice", "Keyboard", "Mark: aa (normal)", ("text", "black", "white", "red", "green", "blue", "yellow", "cyan", "magenta", "gray", "darkgray", "lightgray", "orange", "lightgreen")),
    ("COLOR_KEY_SHIFT",  "color",  "Keyboard", "Mark: Aa (shift)", None),
    ("COLOR_KEY_FN",     "color",  "Keyboard", "Mark: FN", None),
    ("COLOR_KEY_OPT",    "color",  "Keyboard", "Mark: OPT/CTRL/ALT", None),
    # ---- Status bars ----
    ("BARS_CLOCK",         "bool", "Bars", "Status bars on clock", None),
    ("BARS_MENU",          "bool", "Bars", "Status bars in menus", None),
    ("BARS_OFFSET_X",      "int",  "Bars", "Bars shift from edge", (0, 60, 1)),
    ("BARS_OFFSET_Y",      "int",  "Bars", "Bars shift down", (0, 20, 1)),
    ("BATTERY_BLUE_PCT",   "int",  "Bars", "Battery blue from (%)", (30, 100, 5)),
    ("BATTERY_GREEN_PCT",  "int",  "Bars", "Battery green from (%)", (10, 95, 5)),
    ("BATTERY_YELLOW_PCT", "int",  "Bars", "Battery yellow from (%)", (5, 90, 5)),
    ("FOCUS_RED_PCT",      "int",  "Bars", "Focus red below (%)", (5, 95, 5)),
    ("FOCUS_YELLOW_PCT",   "int",  "Bars", "Focus yellow below (%)", (10, 99, 5)),
    # ---- Screen ----
    ("SCREEN_DIM_SECONDS", "int", "Screen", "Dim after (s), 0 = never", (0, 600, 5)),
    ("BRIGHTNESS",         "int", "Screen", "Brightness (0 = as is)", (0, 255, 5)),
    ("DIM_BRIGHTNESS",     "int", "Screen", "Dimmed brightness (%)", (0, 100, 5)),
    # ---- Time ----
    ("TIMESYNC_AT_BOOT",    "bool", "Time", "WiFi time sync at start", None),
    ("TIME_UTC_OFFSET_MIN", "int",  "Time", "UTC offset (minutes)", (-720, 840, 30)),
    ("TIME_EU_DST",         "bool", "Time", "EU summer time", None),
    # ---- Audio ----
    ("AUDIO_MIC_MAGNIFICATION", "choice", "Audio", "Microphone gain", (0, 16, 32, 64, 96, 128, 160, 192, 255)),
    ("AUDIO_DEFAULT_VOL",       "int",    "Audio", "Playback volume (%)", (0, 100, 10)),
    ("NOTIFY_SOUND",            "bool",   "Audio", "Notification sound", None),
    ("NOTIFY_VOLUME",           "int",    "Audio", "Notification volume (%)", (0, 100, 10)),
    ("METRO_INTERVAL_S",        "choice", "Audio", "Metronome interval (s)", (1, 2, 5, 30, 60, 120)),
    ("METRO_VOLUME",            "int",    "Audio", "Metronome volume (%)", (0, 100, 10)),
    # ---- Network ----
    ("WIFI_SSID",     "text",   "Network", "Fallback WiFi name", 32),
    ("WIFI_PASSWORD", "secret", "Network", "Fallback WiFi password", 63),
    # ---- Cuckoo (reached from Focus Tools -> Cuckoo Clock) ----
    ("CUCKOO_ENABLED",        "bool", "Cuckoo", "Cuckoo clock", None),
    ("CUCKOO_QUARTERS",       "bool", "Cuckoo", "Quiet tick every 15 min", None),
    ("CUCKOO_QUARTER_VOLUME", "int",  "Cuckoo", "Quarter tick volume (%)", (0, 100, 10)),
    # ---- Power ----
    ("POWER_SAVE",        "bool", "Power", "Save power when dimmed", None),
    ("BATTERY_LOG",       "bool", "Power", "Log battery to SD (10 min)", None),
    ("POWER_LIGHT_SLEEP", "bool", "Power", "Light sleep (experimental)", None),
    ("POWER_UNLOAD_SCREENS", "bool", "Power", "Free screens after use", None),
)
