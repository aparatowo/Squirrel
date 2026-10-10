# ports.py - what the app expects of a device: the interfaces a port (ports/<port>/board.py) has to fill
#
# Nothing here is imported by the app at run time: drivers do not inherit from these classes, they only offer the
# same calls (the app already used them before there were ports; these classes write them down for the next port).
#
# MISSING HARDWARE is not None in the app: each part has a form that does nothing -
#   AudioManager(backend=None)      no microphone / speaker: recording and signals return False
#   led.begin(pin=None)             no LED: status "No LED (port.toml)", signal() returns False
#   buzzer.begin(pin=None)          no buzzer: likewise
#   RTCManager(chip=None)           no hardware clock: only the internal one (set over Wi-Fi or by hand)
#   BatteryMonitor(read=None)       the level is unknown (None): the battery bar stays empty
# so the code that uses them needs no checks.


class Board:
    """ports/<port>/board.py - module-level functions, called in this order:
    begin()                         squirrel_boot.py, before anything else touches the hardware
    begin_buzzer(buzzer, quiet)     first thing in SquirrelApp (a floating buzzer pin could sound)
    make_storage() -> Storage       before the settings are read (they are on it)
    make_input() -> Input
    make_buttons() -> {role: Button}   roles: "quick" (the quick recorder; held at start-up: skip the font)
    clock_chip() -> (factory, name) | (None, None)   factory() -> a hw.rtc_base.TimeProvider of the hardware clock
    make_audio() -> hw.audio_manager.AudioManager
    power_source() -> PowerSource
    begin_led(led, battery)
    motion_off() -> I2C address | None   the motion sensor is switched off until there are features for it
    i2c(name) -> the machine.I2C object of a bus, as it is now
    """


class Display:
    """drivers/<port_config.DISPLAY_DRIVER>.py gives `lcd`, wrapped by gfx.py.  The calls of M5.Lcd the app uses:
    fillScreen(c), fillRect(x, y, w, h, c), drawRect(...), drawLine(...), fillCircle(x, y, r, c), drawCircle(...),
    drawPixel(x, y, c), drawString(text, x, y), setTextColor(fg, bg), setTextSize(n), textWidth(text),
    setBrightness(0..255), getBrightness(), setFont(path) (raises if the driver has no such fonts).
    Colours are 0xRRGGBB.  The size is port_config.DISPLAY_WIDTH x DISPLAY_HEIGHT (gfx.SCREEN_W / SCREEN_H)."""


class Input:
    """Turns the device's keys (or touches) into actions - the strings in MAP_NAV of a keymap: "UP", "ENTER", "ESC",
    "a", "CTRL+s" ...  The screens only ever see these strings."""
    is_text_mode = False           # True while a screen takes text
    modifiers_as_keys = False      # set by the app: Aa / OPT / FN / CTRL / ALT arrive as actions, not as modifiers
    display_modifier = None        # None | "SHIFT" | "FN" | "CTRL" | "OPT" | "ALT": the mark shown while typing
    last_key_code = 0              # the raw code of the last key (the key calibration screen)

    def get_pressed_action(self):
        """(action or None, modifier_changed) - called on every pass of the main loop; must not block."""
        raise NotImplementedError

    def set_text_mode(self, enable):
        raise NotImplementedError

    def acknowledge(self):
        """Clear a pending interrupt, so that its line can wake the chip from light sleep again."""
        return False


class Button:
    held_at_start = False

    def pressed(self):
        """True once per physical press (debounced) - called on every pass of the main loop."""
        raise NotImplementedError


class Storage:
    """Makes port_config.STORAGE_BASE_DIR usable (mounts the card, ...)."""
    is_mounted = False

    def mount(self):
        raise NotImplementedError

    def remount(self):
        raise NotImplementedError


class PowerSource:
    """Each returns None when the device cannot tell."""

    def level(self):
        """Battery level 0..100."""

    def charging(self):
        """True / False."""

    def millivolts(self):
        """Battery voltage."""
