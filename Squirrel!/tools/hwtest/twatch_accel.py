# EXPECT_MACHINE: SPIRAM with ESP32
# SERIAL_LINES: low
# USB_VENDOR: 1a86
# INCLUDE: twatch_screen.py
# twatch_accel.py - tests of the BMA423 accelerometer of the T-Watch 2020 V3 under plain MicroPython (tools/hwtest/run.py)
#
# Only the plain accelerometer: the BMA423's own features (step counter, wrist tilt, double tap) need its ~6 KB
# configuration file loaded first - a later step.  What to do is shown on the watch's screen (twatch_screen.py), and
# vibrations mark the moments: ONE short = take the next position now (6 s to do it), TWO short = measured,
# THREE = the shaking starts.
#
#   t01_identify     chip id, error register, power state                                 (reads only)
#   t02_still        accelerometer on (100 Hz, +-2 g); lying flat: |a| = 1 g? noise         (lay it face up on the desk)
#   t03_orientation  4 positions: face up, face down, standing on its strap edge, on the crown side
#   t04_shake        5 s of shaking: peak acceleration
#   t05_temperature  the sensor's temperature
#   t06_off          accelerometer off again; read back
import time
import math
from machine import I2C, Pin

SDA, SCL, AXP, MOTOR = 21, 22, 0x35, 4
ADDRS = (0x19, 0x18)
REG_CHIP_ID, REG_ERR, REG_DATA, REG_TEMP = 0x00, 0x02, 0x12, 0x22
REG_ACC_CONF, REG_ACC_RANGE, REG_PWR_CONF, REG_PWR_CTRL = 0x40, 0x41, 0x7C, 0x7D
CHIP_ID = 0x13
DEFAULT = ("t01_identify", "t02_still", "t03_orientation", "t04_shake", "t05_temperature", "t06_off")

_bus = None
_addr = None


def result(test, status, details=""):
    print("RESULT|%s|%s|%s" % (test, status, details))


def bus():
    global _bus, _addr
    if _bus is None:
        _bus = I2C(0, sda=Pin(SDA), scl=Pin(SCL), freq=400000)
        try:
            if _bus.readfrom_mem(AXP, 0x03, 1)[0] != 0x41:
                raise OSError
        except OSError:
            raise RuntimeError("no AXP202 on GPIO21/22 - not a T-Watch 2020, nothing done")
        found = _bus.scan()
        for a in ADDRS:
            if a in found:
                _addr = a
                break
    return _bus


def rd(reg, n=1):
    return bus().readfrom_mem(_addr, reg, n)


def wr(reg, value):
    bus().writeto_mem(_addr, reg, bytes([value]))


def buzz(n=1, ms=120):
    p = Pin(MOTOR, Pin.OUT, value=0)
    for _ in range(n):
        p.value(1)
        time.sleep_ms(ms)
        p.value(0)
        time.sleep_ms(180)


def say(text, rows=None):
    """On the console, and (rows: lines of ASCII) on the watch's screen."""
    print("   >> " + text)
    if rows:
        try:
            screen().lines(rows, scale=3)
        except Exception as e:
            print("   (screen: %s)" % e)


def acc():
    """(x, y, z) in g: 12-bit values, left-aligned in 16 bits; +-2 g = 1024 per g."""
    d = rd(REG_DATA, 6)
    out = []
    for i in (0, 2, 4):
        v = d[i] | d[i + 1] << 8
        if v & 0x8000:
            v -= 65536
        out.append((v >> 4) / 1024)
    return tuple(out)


def norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def fmt(v):
    return "x=%+.2f y=%+.2f z=%+.2f |a|=%.2f" % (v[0], v[1], v[2], norm(v))


def sample(seconds):
    out, end = [], time.ticks_add(time.ticks_ms(), int(seconds * 1000))
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        out.append(acc())
        time.sleep_ms(20)
    return out


def mean(s):
    return tuple(sum(v[i] for v in s) / len(s) for i in range(3))


def acc_on():
    wr(REG_PWR_CONF, 0x00)          # advanced power save off
    time.sleep_ms(2)
    wr(REG_ACC_CONF, 0xA8)          # 100 Hz, normal averaging, performance mode
    wr(REG_ACC_RANGE, 0x00)         # +-2 g
    wr(REG_PWR_CTRL, 0x04)          # accelerometer on
    time.sleep_ms(60)


def t01_identify():
    bus()
    if _addr is None:
        result("t01_identify", "FAIL", "no BMA423 at 0x19 / 0x18")
        return False
    cid = rd(REG_CHIP_ID)[0]
    result("t01_identify", "PASS" if cid == CHIP_ID else "FAIL", "chip id 0x%02x at 0x%02x (BMA423 = 0x13)" % (cid, _addr))
    result("t01_identify", "INFO", "error register 0x%02x, PWR_CTRL 0x%02x, PWR_CONF 0x%02x" % (rd(REG_ERR)[0], rd(REG_PWR_CTRL)[0], rd(REG_PWR_CONF)[0]))
    return True


def t02_still():
    if _addr is None and not t01_identify():
        return
    acc_on()
    say("lay the watch FACE UP on the desk; measuring in 6 s", [("AKCELEROMETR", YELLOW), "", "poloz zegarek", "tarcza do gory", "na stole", "", ("pomiar za 6 s", CYAN)])
    buzz(1)
    time.sleep(6)
    s = sample(2)
    buzz(2)
    say("measured", [("ZMIERZONE", GREEN)])
    m = mean(s)
    noise = tuple(math.sqrt(sum((v[i] - m[i]) ** 2 for v in s) / len(s)) for i in range(3))
    if norm(m) < 0.05:
        result("t02_still", "FAIL", "all zero: the accelerometer gives no data without its configuration file?")
        return
    result("t02_still", "PASS" if 0.9 <= norm(m) <= 1.1 else "FAIL", fmt(m))
    result("t02_still", "INFO", "noise (std, g): x=%.4f y=%.4f z=%.4f over %d samples" % (noise + (len(s),)))


POSES = (("face_up", "FACE UP, flat on the desk", ["tarcza", "do GORY", "(na stole)"]),
         ("face_down", "FACE DOWN, flat on the desk", ["tarcza", "w DOL", "(na stole)"]),
         ("standing", "standing upright, 12 o'clock at the top (like a clock on the wall)", ["pionowo,", "jak zegar", "na scianie"]),
         ("crown_up", "on its side, the side button pointing UP", ["na boku,", "przycisk", "do GORY"]))


def countdown(seconds):
    """A big number counting down in the middle of the screen, one per second."""
    for left in range(seconds, 0, -1):
        try:
            sc = screen()
            sc.rect(0, 80, W, 80, BLACK)
            sc.text("%2d" % left, None, 88, 8, CYAN)
        except Exception:
            pass
        time.sleep_ms(1000)


def t03_orientation():
    if _addr is None and not t01_identify():
        return
    acc_on()
    got = {}
    for n, (name, text, rows) in enumerate(POSES, 1):
        say("next: " + text + " - 10 s", [("POZYCJA %d/4" % n, YELLOW), ""] + rows + ["", ("po wibracji: 10 s", CYAN)])
        time.sleep(4)                                      # time to read it (the face-down one cannot be read later)
        buzz(1)
        countdown(10)
        m = mean(sample(1))
        buzz(2)
        say("measured", [("ZMIERZONE", GREEN)])
        got[name] = m
        axis = max(range(3), key=lambda i: abs(m[i]))
        result("t03_orientation", "INFO", "%-9s %s  -> axis %s%s" % (name, fmt(m), "+" if m[axis] > 0 else "-", "xyz"[axis]))
        time.sleep(1)
    up, down = got["face_up"], got["face_down"]
    axis = max(range(3), key=lambda i: abs(up[i]))
    ok = abs(up[axis]) > 0.8 and abs(down[axis]) > 0.8 and up[axis] * down[axis] < 0
    result("t03_orientation", "PASS" if ok else "FAIL",
           "face down detectable: axis %s is %+.2f g face up, %+.2f g face down" % ("xyz"[axis], up[axis], down[axis]))


def t04_shake():
    if _addr is None and not t01_identify():
        return
    acc_on()
    say("three vibrations = SHAKE the watch for 5 s", [("POTRZASANIE", YELLOW), "", "po 3 wibracjach", "potrzasaj", "przez 5 s"])
    time.sleep(4)
    buzz(3, 80)
    peak, end = 0, time.ticks_add(time.ticks_ms(), 5000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        peak = max(peak, norm(acc()))
        time.sleep_ms(10)
    buzz(2)
    say("done", [("KONIEC", GREEN)])
    result("t04_shake", "PASS" if peak > 1.8 else "FAIL", "peak |a| = %.2f g (the +-2 g range clips at 2; shaking should reach it)" % peak)


def t05_temperature():
    if _addr is None and not t01_identify():
        return
    acc_on()
    t = rd(REG_TEMP)[0]
    t = t - 256 if t > 127 else t
    result("t05_temperature", "INFO", "sensor temperature %d C (register + 23)" % (t + 23))


def t06_off():
    if _addr is None and not t01_identify():
        return
    wr(REG_PWR_CTRL, 0x00)
    wr(REG_PWR_CONF, 0x03)          # advanced power save back on (the chip's default)
    result("t06_off", "PASS" if rd(REG_PWR_CTRL)[0] == 0 else "FAIL", "PWR_CTRL 0x%02x after switching off" % rd(REG_PWR_CTRL)[0])


def run(names):
    for name in names or DEFAULT:
        print("\n== " + name)
        try:
            globals()[name]()
        except Exception as e:
            result(name, "FAIL", "%s: %s" % (type(e).__name__, e))
    print("\n== done")
