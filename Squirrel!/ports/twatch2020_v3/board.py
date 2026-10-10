# board.py - the LilyGo T-Watch 2020 V3: puts its hardware together for the app
#
# The pins and addresses come from port_config (port.toml next to this file); every one was confirmed on the watch
# (tools/hwtest/README_PL.md).  Order matters: the AXP202 must power the display (LDO2) before the panel is set up.

import port_config as P

_buses = {}
_axp = None
EARLY_CLOCK = True              # squirrel_boot shows the time before the app is built (seconds after every wake)

# gestures -> the actions the screens know (the Cardputer's keys)
ACTIONS = {"tap": "ENTER", "swipe_up": "UP", "swipe_down": "DOWN", "swipe_right": "ESC", "swipe_left": "RIGHT",
           "long": "OPT"}                         # up / down: the way the finger moves (asked for on 2026-10-10)


def open_i2c(name="sys"):
    from machine import I2C, Pin
    p = "I2C_%s_" % name.upper()
    bus = I2C(getattr(P, p + "ID"), sda=Pin(getattr(P, p + "SDA")), scl=Pin(getattr(P, p + "SCL")), freq=getattr(P, p + "FREQ"))
    _buses[name] = bus
    return bus


def i2c(name="sys"):
    return _buses.get(name)


def axp():
    global _axp
    if _axp is None:
        from drivers.axp202 import AXP202
        _axp = AXP202(_buses.get("sys") or open_i2c("sys"))
    return _axp


def begin():
    """First thing at start-up: the power chip (display power on, stale interrupts cleared), then the panel."""
    from machine import Pin, PWM, SPI
    from drivers.st7789_fb import lcd
    axp().begin()
    spi = SPI(P.DISPLAY_SPI_ID, baudrate=P.DISPLAY_BAUD, polarity=0, phase=0,
              sck=Pin(P.DISPLAY_SCK), mosi=Pin(P.DISPLAY_MOSI), miso=None)    # miso=None: SPI(2)'s default MISO is GPIO19
    lcd.set_layout(getattr(P, "DISPLAY_LAYOUT_HEIGHT", P.DISPLAY_HEIGHT))
    lcd.begin(spi, Pin(P.DISPLAY_CS, Pin.OUT, value=1), Pin(P.DISPLAY_DC, Pin.OUT, value=1),
              PWM(Pin(P.DISPLAY_BACKLIGHT), freq=1000, duty_u16=0), madctl=P.DISPLAY_MADCTL, row_offset=P.DISPLAY_ROW_OFFSET)


def begin_buzzer(buzzer, quiet):
    """The vibration motor, driven like the Cardputer's buzzer (on / off patterns)."""
    from drivers.pin_pulser import PinPulser
    return buzzer.begin(quiet=quiet, pin=P.SIGNAL_BUZZER_PIN, pwm_freq=P.SIGNAL_BUZZER_PWM_FREQ,
                        reserved=(P.I2C_SYS_SDA, P.I2C_SYS_SCL, P.I2C_TOUCH_SDA, P.I2C_TOUCH_SCL), pulser=PinPulser)


def make_storage():
    from drivers.flash_storage import FlashStorage
    return FlashStorage(P.STORAGE_BASE_DIR)


def _touch_reset():
    import time
    from machine import Pin
    rst = Pin(P.INPUT_RST, Pin.OUT, value=0)
    time.sleep_ms(20)
    rst.value(1)
    time.sleep_ms(300)


def make_input():
    """The touch screen: the FT6336 chip under the common touch layer (gestures, coordinates of the layout area)."""
    from drivers.ft6336 import FT6336
    from drivers.st7789_fb import lcd
    from hw.touch_input import TouchInput
    chip = FT6336(lambda: open_i2c(P.INPUT_BUS), reset=_touch_reset)
    return TouchInput(chip, ACTIONS, size=(P.DISPLAY_WIDTH, P.DISPLAY_HEIGHT), px_per_mm=P.DISPLAY_PPI / 25.4,
                      swap_xy=P.INPUT_SWAP_XY, mirror_x=P.INPUT_MIRROR_X, mirror_y=P.INPUT_MIRROR_Y,
                      origin=lcd.layout_origin)


def make_buttons():
    """{role: button}: "back" = the side button (short press)."""
    from drivers.axp_pek import PekButton
    return {"back": PekButton(axp())}


def clock_chip():
    def open_pcf8563():
        from drivers.pcf8563 import PCF8563TimeProvider
        return PCF8563TimeProvider(_buses.get("sys") or open_i2c("sys"))
    return open_pcf8563, "pcf8563"


def make_audio():
    from hw.audio_manager import AudioManager
    return AudioManager(None)                 # the speaker comes later (I2S, LDO4); recording needs a PDM driver


def power_source():
    return axp()


def begin_led(led, battery):
    return led.begin(battery=battery)          # no LED


def arm_light_sleep_wake():
    """Light sleep (POWER_SLEEP light / deep, while dimmed): the side button (ext0) or a touch (ext1) wakes the chip.
    A classic ESP32 takes two such sources this way (Pin.irq(wake=...) runs out of them)."""
    import esp32
    from machine import Pin
    esp32.wake_on_ext0(Pin(P.POWER_MGMT_WAKE_BUTTON, Pin.IN), esp32.WAKEUP_ALL_LOW)
    esp32.wake_on_ext1((Pin(P.INPUT_INT, Pin.IN),), esp32.WAKEUP_ALL_LOW)


def wake_reason():
    """Why the ESP32 started: "alarm" (the clock's alarm), "button" (the side button) after a deep sleep, else None."""
    import machine
    if machine.reset_cause() != machine.DEEPSLEEP_RESET:
        return None
    r = machine.wake_reason()
    if r == machine.EXT1_WAKE:
        return "alarm"
    if r == machine.EXT0_WAKE:
        return "button"
    return "other"


def deep_sleep(alarm, touch=None):
    """Sleep for real.  alarm: (year, month, day, hour, minute) for the clock's alarm, or None (only the button wakes).
    The panel, its power and the amplifier go off, the touch controller hibernates.  Does not return: waking restarts
    the ESP32 (wake_reason() then says why)."""
    import esp32
    import machine
    from machine import Pin
    from drivers.st7789_fb import lcd
    clock = clock_chip()[0]()
    clock.set_alarm(None if alarm is None else (alarm[0], alarm[1], alarm[2], alarm[3], alarm[4], 0, 0, 0))
    lcd.sleep()
    a = axp()
    a.display_power(False)
    a.audio_power(False)
    if touch is not None:
        touch.hibernate()
    a.clear_irqs()
    esp32.wake_on_ext0(Pin(P.POWER_MGMT_WAKE_BUTTON, Pin.IN), esp32.WAKEUP_ALL_LOW)
    if alarm is not None:
        esp32.wake_on_ext1((Pin(P.POWER_MGMT_WAKE_ALARM, Pin.IN),), esp32.WAKEUP_ALL_LOW)
    else:
        esp32.wake_on_ext1(None, esp32.WAKEUP_ALL_LOW)      # (light sleep had the touch line on it)
    machine.deepsleep()


def motion_off():
    from drivers import bma423
    return bma423.off(_buses.get("sys"), P.MOTION_ADDRS)
