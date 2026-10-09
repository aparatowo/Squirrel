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

SETTINGS = (
    # ---- Display ----
    ("COLOR_FG",      "color", "Display", "Main colour", None),
    ("COLOR_ACCENT",  "color", "Display", "Accent colour", None),
    ("COLOR_WARNING", "color", "Display", "Warning colour", None),
    ("COLOR_ERROR",   "color", "Display", "Error colour", None),
    ("COLOR_BG",      "color", "Display", "Background colour", None),
    ("FONT_ENABLED",  "bool",  "Display", "Use font", None),
    ("CLOCK_FOOTER_TEXT",     "text", "Display", "Clock footer text", 30),
    ("CLOCK_DATE_OFFSET_X",   "int", "Display", "Clock date X", (-40, 40, 1)),
    ("CLOCK_DATE_OFFSET_Y",   "int", "Display", "Clock date Y", (-40, 40, 1)),
    ("CLOCK_TIME_OFFSET_X",   "int", "Display", "Clock time X", (-60, 60, 1)),
    ("CLOCK_TIME_OFFSET_Y",   "int", "Display", "Clock time Y", (-40, 40, 1)),
    ("CLOCK_FOOTER_OFFSET_X", "int", "Display", "Clock footer X", (-60, 60, 1)),
    ("CLOCK_FOOTER_OFFSET_Y", "int", "Display", "Clock footer Y", (-40, 40, 1)),
    ("VIEW_FOOTER_OFFSET_X",  "int", "Display", "Viewer footer X", (-20, 60, 1)),
    ("VIEW_FOOTER_OFFSET_Y",  "int", "Display", "Viewer footer Y", (90, 130, 1)),
    # ---- Notes and To-Do ----
    ("TODO_MAX_CHARS",      "int", "Notes", "To-Do max length", (20, 500, 10)),
    ("TODO_TITLE_MAX_LEN",  "int", "Notes", "To-Do title length", (8, 30, 1)),
    ("NOTE_TITLE_MAX_LEN",  "int", "Notes", "Note title length", (8, 40, 1)),
    ("NOTE_BODY_MAX_CHARS", "int", "Notes", "Note max length", (100, 2000, 50)),
    ("MIND_DUMP_MAX_CHARS", "int", "Notes", "Mind Dump length", (50, 500, 10)),
    ("TODO_KEEP_DAYS",      "int", "Notes", "Keep done To-Dos", (1, 60, 1)),
    # ---- Focus ----
    ("FOCUS_GOAL_MINUTES", "int", "Focus", "Daily focus goal", (10, 720, 10)),
    ("ROUTINE_SNOOZE_MIN",  "int", "Focus", "Routine snooze", (1, 60, 1)),
    ("POMODORO_WORK_MIN",   "int", "Focus", "Pomodoro work", (1, 90, 1)),
    ("POMODORO_BREAK_MIN",  "int", "Focus", "Pomodoro break", (1, 30, 1)),
    ("POMODORO_LONG_BREAK_MIN", "int", "Focus", "Long break", (1, 60, 1)),
    ("POMODORO_CYCLES",     "int", "Focus", "Pomodoro blocks", (1, 8, 1)),
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
    # ---- Audio ----
    ("AUDIO_MIC_MAGNIFICATION", "choice", "Audio", "Microphone gain", (0, 16, 32, 64, 96, 128, 160, 192, 255)),
    ("AUDIO_DEFAULT_VOL",       "int",    "Audio", "Playback volume", (0, 100, 10)),
    ("NOTIFY_SOUND",            "bool",   "Audio", "Notification sound", None),
    ("NOTIFY_VOLUME",           "int",    "Audio", "Notify volume", (0, 100, 10)),
    ("METRO_INTERVAL_S",        "choice", "Audio", "Metronome interval", (0.125, 0.25, 0.5, 1, 2, 5, 30, 60, 120)),
    ("METRO_VOLUME",            "int",    "Audio", "Metronome volume", (0, 100, 10)),
    # ---- Network ----
    ("WIFI_SSID",     "text",   "Network", "Fallback WiFi name", 32),
    ("WIFI_PASSWORD", "secret", "Network", "Fallback password", 63),
    # ---- Cuckoo (reached from Focus Tools -> Cuckoo Clock) ----
    ("CUCKOO_ENABLED",        "bool", "Cuckoo", "Cuckoo clock", None),
    ("CUCKOO_QUARTERS",       "bool", "Cuckoo", "Quarter tick", None),
    ("CUCKOO_QUARTER_VOLUME", "int",  "Cuckoo", "Quarter volume", (0, 100, 10)),
    # ---- Buzzer (Personalize, with its status; tests in Settings -> Experimental) ----
    ("BUZZER_NOTIFY",         "bool",   "Buzzer", "Notifications", None),
    ("BUZZER_NOTIFY_MODE",    "choice", "Buzzer", "Notify: mode", BUZZER_MODES),
    ("BUZZER_INTERVALS",      "bool",   "Buzzer", "Pomodoro/Training", None),
    ("BUZZER_INTERVALS_MODE", "choice", "Buzzer", "Pomodoro: mode", BUZZER_MODES),
    ("BUZZER_METRONOME",      "bool",   "Buzzer", "Metronome", None),
    ("BUZZER_METRONOME_MODE", "choice", "Buzzer", "Metronome: mode", BUZZER_MODES),
    ("BUZZER_CUCKOO",         "bool",   "Buzzer", "Cuckoo clock", None),
    ("BUZZER_CUCKOO_MODE",    "choice", "Buzzer", "Cuckoo: mode", BUZZER_MODES),
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
    ("LED_BREATHING",       "bool",   "LED", "Breathing light", None),
    ("LED_CHARGING",        "bool",   "LED", "Charging light", None),
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
    ("POWER_LIGHT_SLEEP", "bool", "Power", "Light sleep", None),
    ("POWER_UNLOAD_SCREENS", "bool", "Power", "Free screens", None),
)

# Shown when a setting is opened in Personalize (and as a comment in config.txt).  At most 38 characters per line; a
# second line after "\n" is shown on the screens that have room for it.
HELP = {
    "FONT_ENABLED":           "Polish letters. Takes effect after\na restart (hold G0 at start to skip).",
    "CLOCK_DATE_OFFSET_X":    "Pixels; more = to the right",
    "CLOCK_DATE_OFFSET_Y":    "Pixels; more = lower",
    "CLOCK_TIME_OFFSET_X":    "Pixels; more = to the right",
    "CLOCK_TIME_OFFSET_Y":    "Pixels; more = lower",
    "CLOCK_FOOTER_OFFSET_X":  "Pixels; more = to the right",
    "CLOCK_FOOTER_OFFSET_Y":  "Pixels; more = lower",
    "VIEW_FOOTER_OFFSET_X":   "Note viewer footer. Pixels;\nmore = to the right",
    "VIEW_FOOTER_OFFSET_Y":   "Note viewer footer. Pixels;\nmore = lower",
    "TODO_MAX_CHARS":         "Characters in one To-Do",
    "TODO_TITLE_MAX_LEN":     "Characters in a To-Do title",
    "NOTE_TITLE_MAX_LEN":     "Characters in a note title",
    "NOTE_BODY_MAX_CHARS":    "Characters in one note",
    "MIND_DUMP_MAX_CHARS":    "Characters in one thought",
    "TODO_KEEP_DAYS":         "Days a done To-Do stays, then it goes",
    "FOCUS_GOAL_MINUTES":     "Minutes of focus a day",
    "ROUTINE_SNOOZE_MIN":     "Minutes before an unanswered\nroutine comes back",
    "POMODORO_WORK_MIN":      "Minutes of one work block",
    "POMODORO_BREAK_MIN":     "Minutes of a short break",
    "POMODORO_LONG_BREAK_MIN": "Minutes; after the last block\nof a round",
    "POMODORO_CYCLES":        "Work blocks in one round",
    "FOCUS_DOT":              "Dot in the corner while the focus\ntimer runs (never on the clock)",
    "COLOR_KEY_NORMAL":       "text = the colour of the text",
    "BARS_CLOCK":             "Battery and focus bars on the clock",
    "BARS_MENU":              "Lines above and below menu titles\nbecome battery and focus bars",
    "BARS_OFFSET_X":          "Pixels from the screen edges",
    "BARS_OFFSET_Y":          "Pixels down",
    "BATTERY_BLUE_PCT":       "Battery % from which the bar is blue",
    "BATTERY_GREEN_PCT":      "Battery % from which it is green",
    "BATTERY_YELLOW_PCT":     "Battery % from which it is yellow;\nbelow: red",
    "FOCUS_RED_PCT":          "Goal % below which the bar is red",
    "FOCUS_YELLOW_PCT":       "Goal % below which it is yellow;\nthen green, blue at 100",
    "SCREEN_DIM_CLOCK_SECONDS": "Seconds without a key; 0 = never",
    "SCREEN_DIM_OTHER_SECONDS": "Seconds without a key; 0 = never",
    "BRIGHTNESS":             "1-255; 0 = as the device starts",
    "DIM_BRIGHTNESS":         "% of normal brightness; 0 = off",
    "TIMESYNC_AT_BOOT":       "Set the clock over WiFi at start\nwhen there is no DS1302",
    "TIME_UTC_OFFSET_MIN":    "Minutes; Poland: 60 (summer time\nis added by EU summer time)",
    "AUDIO_MIC_MAGNIFICATION": "0 = the firmware default",
    "AUDIO_DEFAULT_VOL":      "% for voice notes",
    "NOTIFY_VOLUME":          "% for notification sounds",
    "METRO_INTERVAL_S":       "Seconds between beats;\n0.125 = 1/8 s, 0.25 = 1/4 s, 0.5 = 1/2 s",
    "METRO_VOLUME":           "% for the metronome",
    "WIFI_SSID":              "Used when no saved network is in range",
    "WIFI_PASSWORD":          "Of the fallback network (hidden)",
    "CUCKOO_QUARTERS":        "A quiet tick every 15 minutes",
    "CUCKOO_QUARTER_VOLUME":  "% for the quarter tick",
    "BUZZER_NOTIFY_MODE":     "auto = the feature's own signal",
    "BUZZER_INTERVALS_MODE":  "auto = double, triple (hard block),\nlong (break)",
    "BUZZER_METRONOME_MODE":  "auto = short every 4th beat,\nclick on the others",
    "BUZZER_CUCKOO_MODE":     "auto = double on the hour, click\nfor the quarters",
    "LED_BRIGHTNESS":         "% of full brightness; bright colours are\nlimited by LED_MAX_SUM (nuts.py)",
    "LED_CHARGING":           "Only where charging is reported\n(not on the Cardputer ADV)",
    "LED_BREATHING":          "Green breathing in, blue out",
    "POWER_SAVE":             "Slower CPU while the screen is dimmed",
    "BATTERY_LOG":            "Energy data every 10 min in battery.csv\non the SD card; never sent anywhere",
    "POWER_LIGHT_SLEEP":      "Experimental: sleeps while dimmed;\nthe USB console disconnects",
    "POWER_UNLOAD_SCREENS":   "Rarely used screens leave memory\n(more free heap, slower to open)",
}
