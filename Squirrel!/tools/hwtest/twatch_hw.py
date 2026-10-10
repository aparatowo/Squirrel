# EXPECT_MACHINE: SPIRAM with ESP32
# SERIAL_LINES: low
# USB_VENDOR: 1a86
# INCLUDE: twatch_screen.py
# twatch_hw.py - bringing up the LilyGo T-Watch 2020 V3 under plain MicroPython (ESP32_GENERIC, SPIRAM), test by test
#
# Run with tools/hwtest/run.py.  Each test does ONE thing, says what it changes, and prints RESULT lines; ASK = the
# person at the watch confirms what happened.  The pins are those of PORTING_PL.md (LilyGo's documentation for V3):
# confirming them is the point of these tests.  Before anything else every test checks that an AXP202 answers on the
# I2C bus at 21/22 - on any other board nothing is touched.  The pins were confirmed against CircuitPython's board
# definition lilygo_twatch_2020_v3 (read from the watch on 2026-10-10), which added TOUCH_RST = GPIO14.
#
# What may be WRITTEN (nothing else is, ever): AXP202 register 0x12 bit 2 (LDO2: backlight/display, only when its voltage
# register reads a safe 3.0-3.3 V) and bit 3 (LDO4: the audio amplifier on the V3); 0x28 low nibble only (LDO4's
# voltage, set to 3.3 V exactly as LilyGo's library does for the V3: off, 3.3 V, on); 0x82 (ADC enable); 0x42 (button
# IRQ enable); 0x48-0x4C (IRQ status: writing 1 only clears a pending flag).  LDO3 is unused on the V3 (LilyGo: "No use").
# The voltage registers, DCDC2 / DCDC3 (the ESP32's own supply) and the shutdown settings are only read.
#
#   READING ONLY:  t01_system  t02_i2c  t03_axp  t08_rtc  t13_mic
#   CHANGES:       t04_backlight / t04b_backlight_pin12   LDO2 on, PWM on the backlight pin      (ASK: backlight pulses?)
#                  t05_display / t06_display_rot180        ST7789 init, colour fills, a marker     (ASK: colours, corner)
#                  t07_touch                              digits 1-5 in the corners / centre, then 2x tap, then hold (on screen)
#                  t09_vibration                          GPIO4 pulses                             (ASK: felt it?)
#                  t10_button                             AXP202 power-key events, instructions on screen
#                  t11_speaker                            LDO4 3.3 V on (audio supply), 3 tones in stereo (ASK: heard them?)
#                  t12_battery                            AXP202 ADCs on, battery / USB readings
import time
import struct
from machine import I2C, Pin

SDA, SCL = 21, 22                      # AXP202, BMA423, PCF8563
TOUCH_SDA, TOUCH_SCL, TOUCH_INT, TOUCH_RST = 23, 32, 38, 14
AXP, BMA_ADDRS, RTC, TOUCH = 0x35, (0x19, 0x18), 0x51, 0x38
AXP_INT, RTC_INT, BMA_INT = 35, 37, 39
TFT_SCK, TFT_MOSI, TFT_CS, TFT_DC = 18, 19, 5, 27
BACKLIGHT = 15                         # V3 per LilyGo; V1 used 12 (t04b)
MOTOR = 4
I2S_BCK, I2S_WS, I2S_DOUT = 26, 25, 33
MIC_DATA, MIC_CLK = 2, 0
DEFAULT = ("t01_system", "t02_i2c", "t03_axp", "t08_rtc", "t13_mic")      # the reading-only ones

_bus = None
_WRITABLE = {0x12: 0x0C, 0x28: 0x0F, 0x82: 0xFF, 0x42: 0x03}   # AXP202 register: the bits tests may change
LDO4_MV = (1250, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2500, 2700, 2800, 3000, 3100, 3200, 3300)   # 0x28 & 0x0F
_IRQ_STATUS = range(0x48, 0x4D)        # AXP202 IRQ status 1-5: write 1 = clear (clear_irqs)


def clear_irqs():
    """Clear every pending AXP202 interrupt flag: while one is pending the INT line (GPIO35) stays low."""
    for reg in _IRQ_STATUS:
        bus().writeto_mem(AXP, reg, b"\xff")


def result(test, status, details=""):
    print("RESULT|%s|%s|%s" % (test, status, details))


def bus():
    global _bus
    if _bus is None:
        _bus = I2C(0, sda=Pin(SDA), scl=Pin(SCL), freq=400000)
    return _bus


def require_watch():
    """An AXP202 (chip id 0x41) on 21/22, or stop: this is not a T-Watch 2020."""
    try:
        cid = bus().readfrom_mem(AXP, 0x03, 1)[0]
    except OSError:
        raise RuntimeError("no AXP202 at 0x35 on GPIO21/22 - not a T-Watch 2020, nothing done")
    if cid != 0x41:
        raise RuntimeError("chip at 0x35 has id 0x%02x, not an AXP202 (0x41) - nothing done" % cid)


def axp(reg):
    return bus().readfrom_mem(AXP, reg, 1)[0]


def axp_set_bits(reg, mask, on=True):
    if reg not in _WRITABLE or mask & ~_WRITABLE[reg]:
        raise RuntimeError("AXP202 register 0x%02x bits 0x%02x are not on the list these tests may write" % (reg, mask))
    old = axp(reg)
    new = (old | mask) if on else (old & ~mask & 0xFF)
    if new != old:
        bus().writeto_mem(AXP, reg, bytes([new]))
    return old, axp(reg)


def ldo2_volts():
    return 1.8 + 0.1 * (axp(0x28) >> 4)


def ldo3_volts():
    return 0.7 + 0.025 * (axp(0x29) & 0x7F)


def ldo2_on(test):
    v = ldo2_volts()
    if not 3.0 <= v <= 3.31:
        result(test, "FAIL", "LDO2 is set to %.2f V, not 3.0-3.3 V - not switched on" % v)
        return False
    old, new = axp_set_bits(0x12, 0x04)
    result(test, "INFO", "LDO2 %.2f V: %s" % (v, "was on already" if old & 0x04 else "switched on (0x12: 0x%02x -> 0x%02x)" % (old, new)))
    return True


def motor_pulse(n=1, ms=120):
    p = Pin(MOTOR, Pin.OUT, value=0)
    for _ in range(n):
        p.value(1)
        time.sleep_ms(ms)
        p.value(0)
        time.sleep_ms(150)


# ------------------------------------------------------------------------------------------------ reading only

def t01_system():
    import sys
    import gc
    gc.collect()
    result("t01_system", "INFO", sys.implementation._machine + " / MicroPython %d.%d.%d" % sys.implementation.version[:3])
    import machine
    result("t01_system", "INFO", "CPU %d MHz" % (machine.freq() // 1000000))
    free = gc.mem_free()
    result("t01_system", "PASS" if free > 1000000 else "FAIL", "free heap %d bytes (%s)" % (free, "PSRAM in use" if free > 1000000 else "no PSRAM?"))
    try:
        import esp
        size = esp.flash_size()
        result("t01_system", "PASS" if size >= 16 * 1024 * 1024 else "INFO", "flash %d MB" % (size // 1048576))
    except Exception as e:
        result("t01_system", "INFO", "flash size unknown: %s" % e)


def t02_i2c():
    require_watch()
    found = bus().scan()
    result("t02_i2c", "INFO", "bus 21/22: %s" % [hex(a) for a in found])
    for name, addrs in (("AXP202", (AXP,)), ("BMA423", BMA_ADDRS), ("PCF8563", (RTC,))):
        hit = [a for a in addrs if a in found]
        result("t02_i2c", "PASS" if hit else "FAIL", "%s %s" % (name, ("at 0x%02x" % hit[0]) if hit else "missing"))
    touch_reset()
    tb = I2C(1, sda=Pin(TOUCH_SDA), scl=Pin(TOUCH_SCL), freq=400000)
    tf = tb.scan()
    result("t02_i2c", "INFO", "bus 23/32: %s" % [hex(a) for a in tf])
    result("t02_i2c", "PASS" if TOUCH in tf else "FAIL", "FT6336 touch " + ("at 0x38" if TOUCH in tf else "missing"))


def t03_axp():
    require_watch()
    s0, s1, out = axp(0x00), axp(0x01), axp(0x12)
    result("t03_axp", "PASS", "AXP202 (chip id 0x41)")
    result("t03_axp", "INFO", "USB/VBUS %s, ACIN %s, battery %s, charging %s" % (
        "yes" if s0 & 0x20 else "no", "yes" if s0 & 0x80 else "no", "present" if s1 & 0x20 else "absent", "yes" if s1 & 0x40 else "no"))
    bits = (("EXTEN", 0x01), ("DCDC3", 0x02), ("LDO2", 0x04), ("LDO4", 0x08), ("DCDC2", 0x10), ("LDO3", 0x40))
    result("t03_axp", "INFO", "outputs (0x12=0x%02x): %s" % (out, ", ".join("%s %s" % (n, "on" if out & b else "off") for n, b in bits)))
    result("t03_axp", "INFO", "set voltages: DCDC2 %.3f V, DCDC3 %.3f V, LDO2 %.2f V, LDO3 %.3f V, LDO4 %.2f V (audio on the V3)" % (
        0.7 + 0.025 * (axp(0x23) & 0x3F), 0.7 + 0.025 * (axp(0x27) & 0x7F), ldo2_volts(), ldo3_volts(), LDO4_MV[axp(0x28) & 0x0F] / 1000))
    result("t03_axp", "INFO", "power-key: shutdown after %d s held (0x36=0x%02x) - never hold the side button that long in t10"
           % ((4, 6, 8, 10)[axp(0x36) & 3], axp(0x36)))


def t08_rtc():
    require_watch()
    d = bus().readfrom_mem(RTC, 0x02, 7)

    def bcd(v):
        return (v >> 4) * 10 + (v & 0x0F)
    vl = d[0] & 0x80
    y = 2000 + bcd(d[6]) + (100 if d[5] & 0x80 else 0)
    t = "%04d-%02d-%02d %02d:%02d:%02d" % (y, bcd(d[5] & 0x1F), bcd(d[3] & 0x3F), bcd(d[2] & 0x3F), bcd(d[1] & 0x7F), bcd(d[0] & 0x7F))
    result("t08_rtc", "INFO" if not vl else "FAIL", "PCF8563 reads %s%s" % (t, "  (VL bit: the time is NOT valid, the clock lost power)" if vl else ""))
    time.sleep(2)
    d2 = bus().readfrom_mem(RTC, 0x02, 1)[0]
    result("t08_rtc", "PASS" if (d2 & 0x7F) != (d[0] & 0x7F) else "FAIL", "running: seconds %02x -> %02x after 2 s" % (d[0] & 0x7F, d2 & 0x7F))


def t13_mic():
    from machine import I2S
    has = hasattr(I2S, "PDM") or hasattr(I2S, "PDM_RX")
    result("t13_mic", "INFO" if has else "SKIP",
           "machine.I2S %s PDM - the V3 microphone (PDM, GPIO%d data / GPIO%d clock) %s" % (
               "has" if has else "has no", MIC_DATA, MIC_CLK, "can be tried" if has else "needs a C module (stage 3)"))


# ------------------------------------------------------------------------------------------------ changes something

def _backlight(test, pin_no):
    require_watch()
    if not ldo2_on(test):
        return
    from machine import PWM
    pwm = PWM(Pin(pin_no), freq=1000, duty_u16=0)
    result(test, "INFO", "GPIO%d: 4 blinks (1 s on / 1 s off), then 2 slow fades (3 s up, 3 s down), then fully on" % pin_no)
    for _ in range(4):
        pwm.duty_u16(65535)
        time.sleep_ms(1000)
        pwm.duty_u16(0)
        time.sleep_ms(1000)
    for _ in range(2):
        for d in list(range(0, 65536, 2048)) + list(range(65535, -1, -2048)):
            pwm.duty_u16(d)
            time.sleep_ms(94)
    pwm.duty_u16(65535)
    result(test, "ASK", "did the screen light BLINK 4 times, then FADE in and out twice?" + ("" if pin_no == 12 else " (if not: run t04b_backlight_pin12)"))


def t04_backlight():
    _backlight("t04_backlight", BACKLIGHT)


def t04b_backlight_pin12():
    _backlight("t04b_backlight_pin12", 12)


class _ST7789:
    def __init__(self, madctl, row_offset):
        self.spi = display_spi()
        self.cs = Pin(TFT_CS, Pin.OUT, value=1)
        self.dc = Pin(TFT_DC, Pin.OUT, value=1)
        self.rows = row_offset
        for cmd, data, wait in ((0x01, b"", 150), (0x11, b"", 120), (0x3A, b"\x55", 10), (0x36, bytes([madctl]), 0),
                                (0x21, b"", 0), (0x13, b"", 10), (0x29, b"", 50)):
            self.cmd(cmd, data)
            time.sleep_ms(wait)

    def cmd(self, c, data=b""):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([c]))
        if data:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)

    def rect(self, x, y, w, h, rgb565):
        self.cmd(0x2A, struct.pack(">HH", x, x + w - 1))
        self.cmd(0x2B, struct.pack(">HH", y + self.rows, y + self.rows + h - 1))
        line = struct.pack(">H", rgb565) * w
        self.cs(0)
        self.dc(0)
        self.spi.write(b"\x2c")
        self.dc(1)
        for _ in range(h):
            self.spi.write(line)
        self.cs(1)


def _display(test, madctl, row_offset):
    require_watch()
    if not ldo2_on(test):
        return
    Pin(BACKLIGHT, Pin.OUT, value=1)
    d = _ST7789(madctl, row_offset)
    for name, c in (("RED", 0xF800), ("GREEN", 0x07E0), ("BLUE", 0x001F), ("WHITE", 0xFFFF)):
        print("   >> now: " + name)
        d.rect(0, 0, 240, 240, c)
        time.sleep_ms(2500)
    d.rect(0, 0, 240, 240, 0x0000)
    d.rect(0, 0, 40, 40, 0xFFE0)               # yellow square: top left
    d.rect(200, 200, 40, 40, 0x07FF)           # cyan square: bottom right
    d.rect(100, 0, 40, 10, 0xF800)             # red bar: top edge, middle
    time.sleep_ms(6000)                        # time to look at the markers
    result(test, "INFO", "MADCTL 0x%02x, row offset %d, inversion on, SPI mode 0 at 26.67 MHz" % (madctl, row_offset))
    result(test, "ASK", "were the fills RED, GREEN, BLUE, WHITE (in this order, whole screen)? is the YELLOW square top left, "
                        "CYAN bottom right, RED bar at the top?  any strip of noise?")


def t05_display():
    _display("t05_display", 0x00, 0)


def t06_display_rot180():
    _display("t06_display_rot180", 0xC0, 80)


def touch_reset():
    """Pulse the touch controller's reset line (GPIO14), as LilyGo's code does before using it."""
    rst = Pin(TOUCH_RST, Pin.OUT, value=0)
    time.sleep_ms(20)
    rst.value(1)
    time.sleep_ms(300)


def _touch_bus():
    touch_reset()
    return I2C(1, sda=Pin(TOUCH_SDA), scl=Pin(TOUCH_SCL), freq=400000)


def _touch_point(tb):
    """(x, y) of the first touch point, or None when nothing touches the screen."""
    d = tb.readfrom_mem(TOUCH, 0x02, 5)
    if not d[0] & 0x0F:
        return None
    return (d[1] & 0x0F) << 8 | d[2], (d[3] & 0x0F) << 8 | d[4]


def _wait_release(tb, limit_ms=8000):
    """Wait until the finger is lifted; returns how long it stayed down (ms)."""
    t0 = time.ticks_ms()
    while _touch_point(tb) is not None and time.ticks_diff(time.ticks_ms(), t0) < limit_ms:
        time.sleep_ms(15)
    return time.ticks_diff(time.ticks_ms(), t0)


def _wait_tap(tb, timeout_ms):
    """The point of the next touch (after the screen was free), or None after timeout_ms."""
    _wait_release(tb)
    end = time.ticks_add(time.ticks_ms(), timeout_ms)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        p = _touch_point(tb)
        if p is not None:
            return p
        time.sleep_ms(15)
    return None


def t07_touch():
    require_watch()
    tb = _touch_bus()
    try:
        cid = tb.readfrom_mem(TOUCH, 0xA3, 1)[0]
    except OSError as e:
        result("t07_touch", "FAIL", "no answer from 0x38: %s" % e)
        return
    result("t07_touch", "PASS", "FT6x36 chip id 0x%02x (0x64 = FT6336U)" % cid)
    sc = screen()
    sc.lines([("TEST DOTYKU", YELLOW), "", "stukaj w cyfre,", "ktora sie", "pokaze: 1..5"], scale=3)
    motor_pulse(1)
    time.sleep_ms(4000)
    hits = 0
    for n, where in enumerate(("TL", "TR", "BL", "BR", "C"), 1):
        sc.clear()
        cx, cy = sc.digit(str(n), where)
        p = _wait_tap(tb, 20000)
        if p is None:
            result("t07_touch", "FAIL", "%d (%s): no tap within 20 s" % (n, where))
            continue
        off = int(((p[0] - cx) ** 2 + (p[1] - cy) ** 2) ** 0.5)
        hits += off <= 48
        result("t07_touch", "PASS" if off <= 48 else "FAIL",
               "%d (%s): digit centre %d,%d - tap %d,%d - %d px off" % (n, where, cx, cy, p[0], p[1], off))
        sc.digit(str(n), where, GREEN)
        motor_pulse(1, 60)
        _wait_release(tb)
    # double tap
    sc.clear()
    sc.text("STUKNIJ 2x", None, 16, 3, CYAN)
    sc.text("szybko", None, 200, 2, GRAY)
    sc.digit("6", "C")
    p = _wait_tap(tb, 20000)
    if p is None:
        result("t07_touch", "FAIL", "6 (double tap): no tap within 20 s")
    else:
        t1 = time.ticks_ms()
        _wait_release(tb)
        end = time.ticks_add(t1, 700)
        second = None
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            second = _touch_point(tb)
            if second is not None:
                break
            time.sleep_ms(10)
        if second is not None:
            result("t07_touch", "PASS", "6 (double tap): second tap %d ms after the first, at %d,%d" % (time.ticks_diff(time.ticks_ms(), t1), second[0], second[1]))
            sc.digit("6", "C", GREEN)
            motor_pulse(2, 60)
        else:
            result("t07_touch", "FAIL", "6 (double tap): only one tap within 700 ms")
        _wait_release(tb)
    # hold
    sc.clear()
    sc.text("PRZYTRZYMAJ", None, 16, 3, CYAN)
    sc.text("2 sekundy", None, 200, 2, GRAY)
    sc.digit("7", "C")
    p = _wait_tap(tb, 20000)
    if p is None:
        result("t07_touch", "FAIL", "7 (hold): no touch within 20 s")
    else:
        t0, buzzed = time.ticks_ms(), False
        while _touch_point(tb) is not None and time.ticks_diff(time.ticks_ms(), t0) < 6000:
            if not buzzed and time.ticks_diff(time.ticks_ms(), t0) >= 1500:
                sc.digit("7", "C", GREEN)
                motor_pulse(1, 60)
                buzzed = True
            time.sleep_ms(15)
        held = time.ticks_diff(time.ticks_ms(), t0)
        result("t07_touch", "PASS" if held >= 1500 else "FAIL", "7 (hold): held %d ms at %d,%d (1500 ms needed)" % (held, p[0], p[1]))
    sc.lines([("DOTYK:", YELLOW), "koniec"], scale=3)
    result("t07_touch", "INFO", "%d of 5 digits hit within 48 px" % hits)


def t09_vibration():
    require_watch()
    result("t09_vibration", "INFO", "GPIO%d: 3 short pulses, then 1 long" % MOTOR)
    motor_pulse(3, 150)
    time.sleep_ms(400)
    motor_pulse(1, 600)
    result("t09_vibration", "ASK", "did you feel 3 short vibrations and 1 long one?")


def t10_button():
    """The side button is the AXP202's power key.  Seen on this watch: a press sets the PEK falling / rising edge flags
    (IRQ status 5, 0x4C bits 5 / 6) whether or not they are enabled; the short / long press flags (0x4A bits 1 / 0) are
    reported too when they come."""
    require_watch()
    old, _ = axp_set_bits(0x42, 0x03)          # IRQ: power key short (bit 1) and long (bit 0) press
    clear_irqs()
    irq = Pin(AXP_INT, Pin.IN)
    result("t10_button", "INFO", "INT GPIO%d after clearing: %d (1 = idle)" % (AXP_INT, irq.value()))
    sc = screen()
    sc.lines([("PRZYCISK BOCZNY", YELLOW), "", "1) 2x krotko", "2) 1x trzymaj", "   ok. 2 s", "",
              ("max 3 s! (wylacza)", RED), "", ("nacisniecia: 0", CYAN)], scale=2, top=20)
    motor_pulse(1)
    presses, short, long_ = [], 0, 0
    down_at = None
    end = time.ticks_add(time.ticks_ms(), 30000)
    while time.ticks_diff(end, time.ticks_ms()) > 0 and len(presses) < 3:
        s3, s5 = axp(0x4A), axp(0x4C)
        now = time.ticks_ms()
        if s5 & 0x20 and down_at is None:              # falling edge: pressed
            down_at = now
        if s5 & 0x40 and down_at is not None:          # rising edge: released
            presses.append(time.ticks_diff(now, down_at))
            down_at = None
            result("t10_button", "INFO", "press %d: held %d ms" % (len(presses), presses[-1]))
            sc.rect(0, 20 + 8 * 18 - 2, W, 20, BLACK)
            sc.text("nacisniecia: %d" % len(presses), None, 20 + 8 * 18, 2, GREEN)
            motor_pulse(1, 60)
        short += 1 if s3 & 0x02 else 0
        long_ += 1 if s3 & 0x01 else 0
        if s3 & 0x03 or s5 & 0x60:
            bus().writeto_mem(AXP, 0x4A, bytes([s3 & 0x03]))
            bus().writeto_mem(AXP, 0x4C, bytes([s5 & 0x60]))
        time.sleep_ms(20)
    if not old & 0x03:
        axp_set_bits(0x42, 0x03, on=False)    # as it was
    clear_irqs()
    sc.lines([("PRZYCISK:", YELLOW), "koniec"], scale=3)
    result("t10_button", "PASS" if presses else "FAIL", "%d presses (edges), held %s ms" % (len(presses), presses))
    result("t10_button", "INFO", "short-press flag %d times, long-press flag %d times" % (short, long_))


def t11_speaker():
    require_watch()
    # the V3's amplifier (MAX98357A, 2.5-5.5 V) is powered by LDO4; LilyGo's library: LDO4 off, 3.3 V, on
    old = axp(0x12)
    mv = LDO4_MV[axp(0x28) & 0x0F]
    if mv != 3300:
        axp_set_bits(0x12, 0x08, on=False)
        bus().writeto_mem(AXP, 0x28, bytes([(axp(0x28) & 0xF0) | 0x0F]))
        result("t11_speaker", "INFO", "LDO4 was set to %d mV: now 3300 mV (0x28 = 0x%02x)" % (mv, axp(0x28)))
    axp_set_bits(0x12, 0x08)
    result("t11_speaker", "INFO", "LDO4 %d mV, %s (0x12 = 0x%02x)" % (LDO4_MV[axp(0x28) & 0x0F], "was on" if old & 0x08 else "switched on", axp(0x12)))
    sc = screen()
    sc.lines([("GLOSNIK", YELLOW), "", "za chwile", "3 tony:", "nisko-srednio-", "wysoko"], scale=3)
    time.sleep_ms(2500)
    from machine import I2S
    import math
    rate = 16000
    # STEREO, the same sample in both channels: the MAX98357A plays one channel (or their mix), whichever it is wired for
    i2s = I2S(0, sck=Pin(I2S_BCK), ws=Pin(I2S_WS), sd=Pin(I2S_DOUT), mode=I2S.TX, bits=16, format=I2S.STEREO, rate=rate, ibuf=16000)
    try:
        for n, freq in enumerate((440, 660, 880), 1):
            sc.lines([("GLOSNIK", YELLOW), "", ("ton %d / 3" % n, CYAN), "%d Hz" % freq], scale=3)
            period = rate // freq
            one = bytearray(period * 4)
            for i in range(period):
                v = int(12000 * math.sin(2 * math.pi * i / period))
                struct.pack_into("<hh", one, 4 * i, v, v)
            i2s.write(bytes(one) * (rate * 8 // 10 // period))      # 0.8 s
            time.sleep_ms(250)
        i2s.write(bytes(4 * 800))                                    # silence, so the last tone does not click off
    finally:
        i2s.deinit()
    if not old & 0x08:
        axp_set_bits(0x12, 0x08, on=False)    # the amplifier's supply off again (left at 3.3 V, LilyGo's setting)
    sc.lines([("GLOSNIK:", YELLOW), "slychac bylo", "3 tony?"], scale=3)
    result("t11_speaker", "ASK", "did you hear three tones, low - middle - high?")


def t12_battery():
    require_watch()
    old, _ = axp_set_bits(0x82, 0xCC)          # ADCs: battery voltage + current, VBUS voltage + current
    time.sleep_ms(300)

    def adc12(hi, lo):
        return axp(hi) << 4 | (axp(lo) & 0x0F)
    vbat = adc12(0x78, 0x79) * 1.1
    vbus = adc12(0x5A, 0x5B) * 1.7
    ichg = (axp(0x7A) << 5 | (axp(0x7B) & 0x1F)) * 0.5
    idis = (axp(0x7C) << 5 | (axp(0x7D) & 0x1F)) * 0.5
    pct = axp(0xB9)
    result("t12_battery", "PASS" if 3000 <= vbat <= 4350 else "FAIL", "battery %.0f mV" % vbat)
    result("t12_battery", "INFO", "USB %.0f mV, charging %.1f mA, discharging %.1f mA, fuel gauge %s" % (
        vbus, ichg, idis, "%d %% (raw 0x%02x)" % (pct & 0x7F, pct)))
    result("t12_battery", "INFO", "ADC enable 0x82: 0x%02x -> 0x%02x (left on: a few uA)" % (old, axp(0x82)))


def run(names):
    for name in names or DEFAULT:
        print("\n== " + name)
        try:
            globals()[name]()
        except Exception as e:
            result(name, "FAIL", "%s: %s" % (type(e).__name__, e))
    print("\n== done")
