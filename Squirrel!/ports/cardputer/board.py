# board.py - the M5Stack Cardputer (the first one, not the ADV): puts its hardware together for the app
#
# Like ports/cardputer_adv/board.py, with what this device has instead: the keyboard is a key matrix on GPIOs
# (drivers/hc138_keypad.py, the same key codes and key map as the ADV), the clock a DS3231 on the Grove port, no motion
# sensor and no buzzer.  The UIFlow firmware (M5.begin) sets up the display, the speaker and the microphone itself.

import port_config as P

_buses = {}                     # name -> the machine.I2C object in use


def begin():
    """First thing at start-up: the UIFlow firmware sets up the display, the speaker, the microphone ..."""
    import M5
    M5.begin()


def open_i2c(name="grove"):
    """A new machine.I2C object for the bus `name` ([i2c.<name>] in port.toml); it becomes the one in use."""
    from machine import I2C, Pin
    p = "I2C_%s_" % name.upper()
    bus = I2C(getattr(P, p + "ID"), sda=Pin(getattr(P, p + "SDA")), scl=Pin(getattr(P, p + "SCL")), freq=getattr(P, p + "FREQ"))
    _buses[name] = bus
    return bus


def i2c(name="grove"):
    """The bus `name` as it is now, or None if nothing has opened it."""
    return _buses.get(name)


def begin_buzzer(buzzer, quiet):
    """No buzzer on this device (no free pin): the buzzer says so in Personalize."""
    return buzzer.begin(quiet=quiet)


def make_storage():
    from drivers.sd_spi import SDCardManager
    return SDCardManager(P.STORAGE_SLOT, P.STORAGE_WIDTH, P.STORAGE_SCK, P.STORAGE_MISO, P.STORAGE_MOSI,
                         P.STORAGE_CS, P.STORAGE_FREQ)


def make_input():
    from drivers.hc138_keypad import HC138Keypad
    from ports.cardputer import keymap
    return HC138Keypad(P.INPUT_LINES, P.INPUT_COLS, keymap)


def make_buttons():
    """{role: button}.  Roles: "quick" = the quick recorder (and, held at start-up, skip the font)."""
    from drivers.gpio_button import ButtonPoller
    return {"quick": ButtonPoller(P.BUTTONS_QUICK_PIN)}


def clock_chip(choice=None):
    """(factory, name) of the clock module the user says is plugged in (the setting RTC_CHIP: "ds3231" on the Grove
    port), or (None, None) for "off".  The factory opens it anew at every use and raises OSError when no DS3231 answers;
    nothing of the driver is imported before then."""
    if choice != "ds3231" or "clock.ds3231" not in P.HARDWARE:
        return None, None

    def open_ds3231():
        from drivers.ds3231 import DS3231TimeProvider
        return DS3231TimeProvider(_buses.get(P.CLOCK_DS3231_BUS) or open_i2c(P.CLOCK_DS3231_BUS))
    return open_ds3231, "ds3231"


def make_audio():
    from hw.audio_manager import AudioManager
    from drivers import m5_audio
    return AudioManager(m5_audio.open)


def power_source():
    """An object with level(), charging(), millivolts() - each None when it cannot be read."""
    from drivers import m5_power
    return m5_power


def begin_led(led, battery):
    """Find the LED (hw/led.py) and switch it off."""
    if "signal.led" not in P.HARDWARE:
        return led.begin(battery=battery)
    from drivers.ws2812 import DRIVERS

    def m5_led():
        import M5
        return M5.Led
    return led.begin(battery=battery, pin=P.SIGNAL_LED_PIN, drivers=DRIVERS, fallback=m5_led,
                     min_backlight=P.SIGNAL_LED_MIN_BACKLIGHT, max_sum=P.SIGNAL_LED_MAX_SUM)


def motion_off():
    """There is no motion sensor on this Cardputer."""
    return None
