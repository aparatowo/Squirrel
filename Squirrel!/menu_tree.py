# menu_tree.py - the structure of the menus, as data (edit this file to reshuffle the UI)
#
# Every entry is (label, kind, argument), optionally with a 4th item: a summary shown after the label
# (see MenuScreen._summary), e.g. "quiet:sound" = the days of the sound's quiet hours.
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
        ("Cuckoo Clock", "screen", ("PERSONALIZE", {"groups": ("Cuckoo",), "title": "Cuckoo Clock",
                                                   "back": ("MENU", {"menu_name": "FOCUS"})})),
        ("Routines", "screen", "ROUTINES"),
        ("Pomodoro", "screen", ("INTERVALS", {"mode": "pomodoro"})),
        ("Metronome", "screen", "METRONOME"),
        ("Training", "screen", ("INTERVALS", {"mode": "training"})),
        ("Breathing", "screen", "BREATHING"),
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
        ("Silent mode", "menu", "SILENT"),
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
        ("Upcoming alarms", "screen", "ALARMS"),          # only where the clock has an alarm (features.toml: deep_sleep)
        # the settings of the Time group (UTC offset, summer time, sync at start-up)
        ("Time settings", "screen", ("PERSONALIZE", {"groups": ("Time",), "title": "Time settings",
                                                    "back": ("MENU", {"menu_name": "TIME_DATE"})})),
    ]),
    # Silent hours, separately for the speaker and the buzzer (QUIET_* settings, see quiet_hours.py)
    "SILENT": ("Silent mode", [
        ("Sound", "screen", ("SILENT_MODE", {"channel": "sound"}), "quiet:sound"),
        ("Buzzer", "screen", ("SILENT_MODE", {"channel": "buzzer"}), "quiet:buzzer"),
        ("LED", "screen", ("SILENT_MODE", {"channel": "led"}), "quiet:led"),
    ]),
    # The buzzer soldered to a GPIO (nuts.BUZZER_*): a try of every mode.  Which features may use it, and whether
    # it works at all, is shown in Personalize -> Buzzer.
    # "buzz:<mode>" = play that mode of buzzer.MODES, whatever the settings say
    "BUZZER_TEST": ("Buzzer test", [
        ("Click", "action", "buzz:click"),
        ("Short", "action", "buzz:short"),
        ("Double", "action", "buzz:double"),
        ("Triple", "action", "buzz:triple"),
        ("Long", "action", "buzz:long"),
        ("Alarm", "action", "buzz:alarm"),
        ("SOS", "action", "buzz:sos"),
    ]),
    # Tests of the LED, one thing at a time (screens/led_test_screen.py), and the modes the features use
    "LED_TEST": ("LED test", [
        ("Steady colours", "screen", ("LED_TESTS", {"test": "colors"})),
        ("Blink intervals", "screen", ("LED_TESTS", {"test": "blink"})),
        ("Brightness steps", "screen", ("LED_TESTS", {"test": "steps"})),
        ("Smooth fade", "screen", ("LED_TESTS", {"test": "fade"})),
        ("Modes", "menu", "LED_MODES"),
    ]),
    # "led:<mode>" = light that mode of led.MODES (in green), whatever the settings say
    "LED_MODES": ("LED modes", [
        ("Flash", "action", "led:flash"),
        ("Double", "action", "led:double"),
        ("Triple", "action", "led:triple"),
        ("Long", "action", "led:long"),
        ("Pulse", "action", "led:pulse"),
        ("Alarm", "action", "led:alarm"),
        ("SOS", "action", "led:sos"),
    ]),
    # Features that work but are not finished or fully trusted yet
    "EXPERIMENTAL": ("Experimental", [
        ("Test notification", "action", "test_notification"),
        ("Test sound", "action", "test_sound"),
        ("Buzzer test", "menu", "BUZZER_TEST"),
        ("LED test", "menu", "LED_TEST"),
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
    "SILENT": "SETTINGS",
    "BUZZER_TEST": "EXPERIMENTAL",
    "LED_TEST": "EXPERIMENTAL",
    "LED_MODES": "LED_TEST",
    "TODO": "MAIN",
    "NOTES": "NOTES_ROOT",
    "MIND": "NOTES_ROOT",
    "RECORDS": "NOTES_ROOT",
}


# ---- what the device cannot do is not shown (features.toml -> port_config.HIDDEN_*) ----
# Entries are dropped here, once, so every index the menu screen works with is already that of the visible list.
def _visible(entry, hidden):
    kind, arg = entry[1], entry[2]
    if kind == "menu":
        return arg not in hidden.HIDDEN_MENUS
    if kind == "action":
        return arg not in hidden.HIDDEN_ACTIONS
    if kind == "screen":
        name, kwargs = (arg[0], arg[1]) if isinstance(arg, tuple) else (arg, {})
        groups = kwargs.get("groups")
        if groups and all(g in hidden.HIDDEN_GROUPS for g in groups):
            return False                            # a settings screen with nothing left to set
        return name not in hidden.HIDDEN_SCREENS
    return True


def _filter(menus, hidden):
    if not (hidden.HIDDEN_MENUS or hidden.HIDDEN_SCREENS or hidden.HIDDEN_ACTIONS or hidden.HIDDEN_GROUPS):
        return menus                                # the device has every feature
    out = {k: (title, [e for e in entries if _visible(e, hidden)]) for k, (title, entries) in menus.items()}
    empty = [k for k, (_t, entries) in out.items() if not entries]
    while empty:                                    # a menu left without entries goes from its parent too
        out = {k: (title, [e for e in entries if not (e[1] == "menu" and e[2] in empty)])
               for k, (title, entries) in out.items() if k not in empty}
        empty = [k for k, (_t, entries) in out.items() if not entries]
    return out


import port_config as _port
MENUS = _filter(MENUS, _port)
