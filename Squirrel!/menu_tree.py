# menu_tree.py - the structure of the menus, as data (edit this file to reshuffle the UI)
#
# Every entry is (label, kind, argument):
#   "menu"   - open another menu           (argument = menu id)
#   "screen" - open a screen                (argument = screen name registered in SquirrelApp,
#                                            or (name, {keyword arguments}) to open it with settings)
#   "action" - run a built-in action        (argument = action name, see MenuScreen._run_action)
#   "soon"   - placeholder for a feature that is not built yet
# Numbers in front of the labels are added automatically.

MENUS = {
    "MAIN": ("Squirrel", [
        ("Focus Tools", "menu", "FOCUS"),
        ("Notes", "menu", "NOTES_ROOT"),
        ("To-Do List", "menu", "TODO"),
        ("Settings", "menu", "SETTINGS"),
    ]),
    "FOCUS": ("Focus Tools", [
        ("Routines", "screen", "ROUTINES"),
        ("Pomodoro", "screen", ("INTERVALS", {"mode": "pomodoro"})),
        ("Training", "screen", ("INTERVALS", {"mode": "training"})),
        ("Metronome", "screen", "METRONOME"),
        ("Breathing", "screen", "BREATHING"),
        ("Cuckoo Clock", "screen", ("PERSONALIZE", {"groups": ("Cuckoo",), "title": "Cuckoo Clock",
                                                   "back": ("MENU", {"menu_name": "FOCUS"})})),
        ("Statistics", "screen", "FOCUS_STATS"),
    ]),
    "NOTES_ROOT": ("Notes", [
        ("Text Notes", "menu", "NOTES"),
        ("Mind Dump", "menu", "MIND"),
        ("Voice Notes", "menu", "RECORDS"),
    ]),
    "SETTINGS": ("Settings", [
        ("Personalize", "screen", "PERSONALIZE"),
        ("Connections", "menu", "CONNECTIONS"),
        ("Time and date", "menu", "TIME_DATE"),
        ("Reload config", "action", "reload_config"),
        ("Key Calibration", "screen", "CALIBRATOR"),
        ("Experimental", "menu", "EXPERIMENTAL"),
    ]),
    "CONNECTIONS": ("Connections", [
        ("WiFi networks", "screen", "WIFI_NETWORKS"),
        # the settings of the Network group (the WIFI_SSID / WIFI_PASSWORD fallback), not listed in Personalize
        ("Fallback network", "screen", ("PERSONALIZE", {"groups": ("Network",), "title": "Fallback network",
                                                       "back": ("MENU", {"menu_name": "CONNECTIONS"})})),
    ]),
    "TIME_DATE": ("Time and date", [
        ("Time via WiFi", "screen", "TIME_SYNC"),
        ("Sync RTC (DS1302)", "action", "sync_rtc"),
        ("Set Time", "screen", "SET_TIME"),
        # the settings of the Time group (UTC offset, summer time, sync at start-up)
        ("Time settings", "screen", ("PERSONALIZE", {"groups": ("Time",), "title": "Time settings",
                                                    "back": ("MENU", {"menu_name": "TIME_DATE"})})),
    ]),
    # Features that work but are not finished or fully trusted yet
    "EXPERIMENTAL": ("Experimental", [
        ("Test notification", "action", "test_notification"),
        ("Test sound", "action", "test_sound"),
        ("Font test", "screen", "FONT_TEST"),
    ]),
}

# File-backed lists: id -> (title, file extension).  Their first row is always "+ [New Item]".
COLLECTIONS = {
    "TODO": ("TODOs", ".txt"),
    "NOTES": ("NOTES", ".txt"),
    "MIND": ("Mind Dump", ".txt"),
    "RECORDS": ("RECORDS", ".wav"),
}

# Where ESC / LEFT leads from each menu (MAIN has no parent: it goes back to the clock).
PARENTS = {
    "FOCUS": "MAIN",
    "NOTES_ROOT": "MAIN",
    "SETTINGS": "MAIN",
    "EXPERIMENTAL": "SETTINGS",
    "CONNECTIONS": "SETTINGS",
    "TIME_DATE": "SETTINGS",
    "TODO": "MAIN",
    "NOTES": "NOTES_ROOT",
    "MIND": "NOTES_ROOT",
    "RECORDS": "NOTES_ROOT",
}
