# board.py - the M5Stack Cardputer ADV: puts its hardware together for the app
#
# The only module that knows which drivers this device has.  The pins and addresses come from port_config (generated
# from port.toml next to this file); the drivers (drivers/) get them as arguments.  squirrel_boot.py calls begin(),
# SquirrelApp the make_* / begin_* functions, in the order it always started the hardware in.

import port_config as P

_buses = {}                     # name -> the machine.I2C object in use (the keyboard opens it again after errors)


def begin():
    """First thing at start-up: the UIFlow firmware sets up the display, the power chip, the speaker ..."""
    import M5
    M5.begin()


def open_i2c(name="sys"):
    """A new machine.I2C object for the bus `name` ([i2c.<name>] in port.toml); it becomes the one in use."""
    from machine import I2C, Pin
    p = "I2C_%s_" % name.upper()
    bus = I2C(getattr(P, p + "ID"), sda=Pin(getattr(P, p + "SDA")), scl=Pin(getattr(P, p + "SCL")), freq=getattr(P, p + "FREQ"))
    _buses[name] = bus
    return bus


def i2c(name="sys"):
    """The bus `name` as it is now, or None if nothing has opened it."""
    return _buses.get(name)


def begin_buzzer(buzzer, quiet):
    """Take the buzzer's pin (hw/buzzer.py) - first thing in the app: until then the pin floats and the NPN could sound."""
    from drivers.pin_pulser import PinPulser
    if "signal.buzzer" not in P.HARDWARE:
        return buzzer.begin(quiet=quiet)
    return buzzer.begin(quiet=quiet, pin=P.SIGNAL_BUZZER_PIN, pwm_freq=P.SIGNAL_BUZZER_PWM_FREQ,
                        reserved=(P.I2C_SYS_SDA, P.I2C_SYS_SCL), pulser=PinPulser)


def make_storage():
    from drivers.sd_spi import SDCardManager
    return SDCardManager(P.STORAGE_SLOT, P.STORAGE_WIDTH, P.STORAGE_SCK, P.STORAGE_MISO, P.STORAGE_MOSI,
                         P.STORAGE_CS, P.STORAGE_FREQ)


def make_input():
    from drivers.tca8418_keypad import TCA8418Keypad
    from ports.cardputer_adv import keymap
    return TCA8418Keypad(lambda: open_i2c(P.INPUT_BUS), P.INPUT_ADDR, keymap)


def make_buttons():
    """{role: button}.  Roles: "quick" = the quick recorder (and, held at start-up, skip the font)."""
    from drivers.gpio_button import ButtonPoller
    return {"quick": ButtonPoller(P.BUTTONS_QUICK_PIN)}


def clock_chip():
    """(factory, name) of the hardware clock, or (None, None).  The factory opens it anew at every use."""
    if "clock" not in P.HARDWARE:
        return None, None

    def open_ds1302():
        from drivers.ds1302 import DS1302TimeProvider
        return DS1302TimeProvider(P.CLOCK_CLK, P.CLOCK_DAT, P.CLOCK_RST)
    return open_ds1302, "ds1302"


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
    """Switch the motion sensor off (it is not used yet); returns its I2C address, or None if it did not answer."""
    from drivers import bmi270
    return bmi270.off(i2c(P.MOTION_BUS), P.MOTION_ADDRS)
