# EXPECT_MACHINE: Cardputer
# cardputer_hw.py - the first try of new Cardputer hardware (run with tools/hwtest/run.py): the DS3231 clock on the
# Grove port (both Cardputers) and the key matrix of the first Cardputer (ports/cardputer, drivers/hc138_keypad.py)
#
# Runs on the Squirrel! firmware: run.py stops the app (Ctrl-C), these tests run, the device is restarted afterwards.
# Instructions appear on the Cardputer's screen.
#
#   t01_grove     the Grove port's I2C bus (G2 = SDA, G1 = SCL): what answers                   (reads only)
#   t02_ds3231    the DS3231: its time, OSF (the time lost), the temperature                     (reads only)
#   t03_alarm     Alarm 2 armed for the next minute: does A2F come?  Disarmed afterwards        (~1 min; not by default)
#   t04_keys      the first Cardputer: 20 s of pressing keys - each one's code and action      (press keys; SKIP on the ADV)
#   t05_led       the LED on G21: red, green, blue, off                                          (look at it)
#   t06_charging  60 s of the battery voltage and the USB host check (drivers/m5_power.py)   (plug / unplug when told)
#   t08_levels    red 255, 64, 32, 16, 8, 4 at back-light 255: the faintest still seen          (look at it)
#   t09_screen_off  the LED breathing up to 80 with the screen off: back-light 0 / panel off / power save
#                 (2026-10-20, ADV: dark with the back-light at 0; lit only while the screen is lit too)
import time
import sys
from machine import I2C, Pin

GROVE = (1, 2, 1)               # bus id, SDA, SCL - as ports/cardputer*/port.toml [i2c.grove]
DS3231 = 0x68
DEFAULT = ("t01_grove", "t02_ds3231", "t04_keys", "t05_led")

_i2c = None


def result(test, status, details=""):
    print("RESULT|%s|%s|%s" % (test, status, details))


def screen(*lines):
    for l in lines:
        print("   >> " + l)
    try:
        from M5 import Lcd
        Lcd.fillScreen(0x000000)
        Lcd.setTextSize(2)
        Lcd.setTextColor(0xFFA500, 0x000000)
        for i, l in enumerate(lines):
            Lcd.drawString(l, 4, 6 + 22 * i)
    except Exception:
        pass


def bus():
    global _i2c
    if _i2c is None:
        _i2c = I2C(GROVE[0], sda=Pin(GROVE[1]), scl=Pin(GROVE[2]), freq=400000)
    return _i2c


def led_driver():
    """The LED's driver: the stopped app's own (its RMT channel stays taken), else a new one."""
    try:
        import sys
        hw = sys.modules["hw.led"].led._hw
        if hw is not None and hasattr(hw, "show"):
            return hw, False
    except Exception:
        pass
    from drivers.ws2812 import DRIVERS
    for make in DRIVERS:
        try:
            return make(21), True
        except Exception as e:
            result("led", "INFO", "%s: %s" % (getattr(make, "name", make), e))
    return None, False


def clock():
    from drivers.ds3231 import DS3231TimeProvider
    return DS3231TimeProvider(bus())


# ------------------------------------------------------------------------------------------------ tests

def t01_grove():
    found = bus().scan()
    result("t01_grove", "INFO", "I2C scan %s" % [hex(a) for a in found])
    if DS3231 in found:
        result("t01_grove", "PASS", "something answers at 0x68 (DS3231)")
    else:
        result("t01_grove", "FAIL", "nothing at 0x68: is the module on the Grove port, SDA / SCL the right way round?")


def t02_ds3231():
    c = clock()
    dt = c.get_datetime()
    result("t02_ds3231", "INFO", "chip time %04d-%02d-%02d %02d:%02d:%02d, weekday %d" % (dt[:6] + (dt[6],)))
    try:
        c.read_valid()
        result("t02_ds3231", "PASS", "the time is valid (OSF clear, plausible)")
    except OSError as e:
        result("t02_ds3231", "INFO", "not valid yet: %s - set the time in Squirrel! (it is written to the chip)" % e)
    t0 = c.get_datetime()[5]
    time.sleep_ms(2100)
    t1 = c.get_datetime()[5]
    ticks = (t1 - t0) % 60
    result("t02_ds3231", "PASS" if ticks in (2, 3) else "FAIL", "the seconds went %d -> %d in 2.1 s" % (t0, t1))
    result("t02_ds3231", "INFO", "temperature %.2f C" % c.temperature())


def t03_alarm():
    c = clock()
    dt = c.get_datetime()
    m = (dt[4] + 1) % 60
    h = (dt[3] + (1 if m == 0 else 0)) % 24
    c.set_alarm((dt[0], dt[1], dt[2], h, m, 0, 0, 0))           # (past midnight the date would be off: run it by day)
    screen("Alarm test", "armed for %02d:%02d" % (h, m), "wait up to 70 s")
    end = time.ticks_add(time.ticks_ms(), 70000)
    fired = False
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        if c.alarm_fired():
            fired = True
            break
        time.sleep_ms(500)
    now = c.get_datetime()
    c.set_alarm(None)
    result("t03_alarm", "PASS" if fired else "FAIL",
           "A2F %s at %02d:%02d:%02d; disarmed again" % ("came" if fired else "did NOT come", now[3], now[4], now[5]))


def t04_keys():
    if "ADV" in sys.implementation._machine:
        result("t04_keys", "SKIP", "the ADV's keyboard is a TCA8418, not the key matrix")
        return
    from drivers.hc138_keypad import HC138Keypad
    from ports.cardputer import keymap
    import port_config as P
    kb = HC138Keypad(P.INPUT_LINES, P.INPUT_COLS, keymap)
    kb.modifiers_as_keys = True                                  # Aa, FN, CTRL ... come as keys too
    screen("Key test", "press keys for 20 s", "(each corner, Aa, FN,", " ENTER, SPACE ...)")
    seen = []
    end = time.ticks_add(time.ticks_ms(), 20000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        action, _changed = kb.get_pressed_action()
        if action:
            seen.append(action)
            result("t04_keys", "INFO", "code %d -> %r" % (kb.last_key_code, action))
            screen("Key test", "code %d" % kb.last_key_code, "-> %s" % action)
        time.sleep_ms(10)
    result("t04_keys", "PASS" if seen else "FAIL", "%d keys: %s" % (len(seen), " ".join(seen)))
    result("t04_keys", "ASK", "did every key give the action printed on it?")


def t05_led():
    led, own = led_driver()
    if led is None:
        result("t05_led", "FAIL", "no LED driver works on G21")
        return
    for name, rgb in (("red", 0x400000), ("green", 0x004000), ("blue", 0x000040)):
        screen("LED test", name)
        led.show(rgb)
        time.sleep_ms(1200)
    led.show(0)
    if own:
        led.release()
    result("t05_led", "ASK", "did the LED show red, green, blue and go dark? (%s)" % led.name)


def t06_charging():
    from drivers import m5_power
    from hw.battery import ChargeGuess
    g = ChargeGuess()
    screen("Charging test", "60 s: plug the USB", "in and out (a charger", "and a computer)")
    last = None
    for i in range(60):
        mv, usb = m5_power.millivolts(), m5_power.usb_host()
        guess = g.feed(mv, usb) if i % 10 == 0 else g.charging        # the app reads every 10 s
        state = (usb, guess)
        if state != last or i % 10 == 0:
            result("t06_charging", "INFO", "%2d s: %s mV, level %s %%, USB host %s, guess %s, M5 charging %s" % (
                i, mv, m5_power.level(), usb, guess, m5_power.charging()))
            last = state
        time.sleep(1)
    result("t06_charging", "ASK", "did 'USB host' follow the computer, and the guess the charger (within ~20 s)?")


GLOW = 80                       # the peak of the breathing in t09 (what a weak LED signal would have been)


def t08_levels():
    """Back-light 255; red 255 (does the LED take frames at all?), then 64 ... 4: the faintest that is still seen."""
    from M5 import Lcd
    led, own = led_driver()
    if led is None:
        result("t08_levels", "FAIL", "no LED driver works on G21")
        return
    before = Lcd.getBrightness()
    Lcd.setBrightness(255)
    for level in (255, 64, 32, 16, 8, 4):
        screen("LED levels", "back-light 255", "red %d / 255" % level)
        for _ in range(6):
            led.show(level << 16)
            time.sleep_ms(500)
    led.show(0)
    if own:
        led.release()
    Lcd.setBrightness(before)
    result("t08_levels", "ASK", "the faintest red level still seen?")


def _breathe(led, seconds, peak=GLOW):
    """Red rising 0 -> peak -> 0 every 2 s, frames every 40 ms (as the app's pulse)."""
    end = time.ticks_add(time.ticks_ms(), int(seconds * 1000))
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        t = time.ticks_ms() % 2000
        level = peak * (t if t < 1000 else 2000 - t) // 1000
        led.show(max(1, level) << 16)
        time.sleep_ms(40)
    led.show(0)


def t09_screen_off():
    """The LED breathing (red up to GLOW) with the screen off, three ways: A back-light 0; B the panel switched off
    (ST7789 DISPOFF) with the back-light on; C M5GFX power save with the back-light on.  Which of them shows the LED,
    and is the screen dark in B and C?"""
    from M5 import Lcd
    led, own = led_driver()
    if led is None:
        result("t09_screen_off", "FAIL", "no LED driver works on G21")
        return
    before = Lcd.getBrightness()

    def dispoff():
        Lcd.setBrightness(255)
        Lcd.writeCommand(0x28)

    def dispon():
        Lcd.writeCommand(0x29)

    def save_on():
        Lcd.powerSaveOn()
        Lcd.setBrightness(255)

    for name, setup, undo in (("A back-light 0", lambda: Lcd.setBrightness(0), lambda: None),
                              ("B panel off, light 255", dispoff, dispon),
                              ("C power save, light 255", save_on, Lcd.powerSaveOff)):
        print("   >> " + name)
        Lcd.setBrightness(255)
        screen("Next:", name, "in 2 s")
        time.sleep(2)
        try:
            setup()
        except Exception as e:
            result("t09_screen_off", "INFO", "%s: %s" % (name, e))
        _breathe(led, 8)
        try:
            undo()
        except Exception as e:
            result("t09_screen_off", "INFO", "%s undo: %s" % (name, e))
    Lcd.setBrightness(before)
    if own:
        led.release()
    result("t09_screen_off", "ASK", "in which of A / B / C did the LED breathe, and was the screen dark in B and C?")


def run(names):
    for name in names or DEFAULT:
        print("\n== " + name)
        try:
            globals()[name]()
        except Exception as e:
            result(name, "FAIL", "%s: %s" % (type(e).__name__, e))
    print("\n== done")
