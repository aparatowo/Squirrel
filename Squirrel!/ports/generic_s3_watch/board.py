# board.py - a generic ESP32-S3 smartwatch: puts its hardware together for the app (EXPERIMENTAL, see port.toml)
#
# The pins and addresses come from port_config (port.toml next to this file).  No power-management chip: the panel
# and the touch controller are powered from the start, the battery is read on an ADC pin, the button is a GPIO.
import port_config as P

_buses = {}
_battery = None
EARLY_CLOCK = False             # no hardware clock: squirrel_boot has no time to show before the app

# gestures -> the actions the screens know (the Cardputer's keys), as on the T-Watch
ACTIONS = {"tap": "ENTER", "swipe_up": "UP", "swipe_down": "DOWN", "swipe_right": "ESC", "swipe_left": "RIGHT",
           "long": "OPT"}


def open_i2c(name="touch"):
    from machine import I2C, Pin
    p = "I2C_%s_" % name.upper()
    bus = I2C(getattr(P, p + "ID"), sda=Pin(getattr(P, p + "SDA")), scl=Pin(getattr(P, p + "SCL")), freq=getattr(P, p + "FREQ"))
    _buses[name] = bus
    return bus


def i2c(name="touch"):
    return _buses.get(name)


def _pulse(pin_no, low_ms=20, after_ms=120):
    import time
    from machine import Pin
    rst = Pin(pin_no, Pin.OUT, value=0)
    time.sleep_ms(low_ms)
    rst.value(1)
    time.sleep_ms(after_ms)


def begin():
    """First thing at start-up: the panel (reset, then set up)."""
    from machine import Pin, PWM, SPI
    from drivers.st7789_fb import lcd
    if getattr(P, "DISPLAY_RST", None) is not None:
        _pulse(P.DISPLAY_RST)
    spi = SPI(P.DISPLAY_SPI_ID, baudrate=P.DISPLAY_BAUD, polarity=0, phase=0,
              sck=Pin(P.DISPLAY_SCK), mosi=Pin(P.DISPLAY_MOSI), miso=None)
    lcd.set_layout(getattr(P, "DISPLAY_LAYOUT_HEIGHT", P.DISPLAY_HEIGHT))
    lcd.begin(spi, Pin(P.DISPLAY_CS, Pin.OUT, value=1), Pin(P.DISPLAY_DC, Pin.OUT, value=1),
              PWM(Pin(P.DISPLAY_BACKLIGHT), freq=1000, duty_u16=0), madctl=P.DISPLAY_MADCTL, row_offset=P.DISPLAY_ROW_OFFSET)


def begin_buzzer(buzzer, quiet):
    """No vibration motor here (a watch with one: [signal.buzzer] in port.toml and the T-Watch's begin_buzzer)."""
    return buzzer.begin(quiet=quiet, pin=None)


def make_storage():
    from drivers.flash_storage import FlashStorage
    return FlashStorage(P.STORAGE_BASE_DIR)


def make_input():
    """The touch screen: the CST816 under the common touch layer (gestures, coordinates of the layout area)."""
    from drivers.cst816 import CST816
    from drivers.st7789_fb import lcd
    from hw.touch_input import TouchInput
    reset = (lambda: _pulse(P.INPUT_RST, 10, 50)) if getattr(P, "INPUT_RST", None) is not None else None
    chip = CST816(lambda: open_i2c(P.INPUT_BUS), reset=reset, addr=P.INPUT_ADDR)
    return TouchInput(chip, ACTIONS, size=(P.DISPLAY_WIDTH, P.DISPLAY_HEIGHT), px_per_mm=P.DISPLAY_PPI / 25.4,
                      swap_xy=P.INPUT_SWAP_XY, mirror_x=P.INPUT_MIRROR_X, mirror_y=P.INPUT_MIRROR_Y,
                      origin=lcd.layout_origin)


def make_buttons():
    """{role: button}: "back" = the side button (short press)."""
    from drivers.gpio_button import ButtonPoller
    return {"back": ButtonPoller(P.BUTTONS_BACK_PIN)}


def clock_chip(choice=None):
    return None, None                           # no hardware clock (see port.toml [clock])


def make_audio():
    from hw.audio_manager import AudioManager
    return AudioManager(None)                    # no speaker / microphone driver yet


def power_source():
    global _battery
    if _battery is None:
        from drivers.adc_battery import AdcBattery
        _battery = AdcBattery(P.POWER_PIN, divider=P.POWER_DIVIDER)
    return _battery


def begin_led(led, battery):
    return led.begin(battery=battery)            # no LED


def motion_off():
    return None                                  # not used yet
