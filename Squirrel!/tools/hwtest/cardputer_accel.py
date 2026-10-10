# EXPECT_MACHINE: Cardputer-ADV
# cardputer_accel.py - tests of the BMI270 motion sensor of the Cardputer ADV (run with tools/hwtest/run.py)
#
# Runs on the Squirrel! firmware: run.py stops the app (Ctrl-C), these tests run, the device is restarted afterwards.
# M5.begin() (at every start) has already loaded the sensor's configuration file; Squirrel! then switches the sensor's
# power off (hw/power.py).  The tests switch it on, measure, and switch it off again as the app leaves it.
# Instructions appear on the Cardputer's screen, with a countdown.
#
#   t01_identify     chip id, configuration loaded?, M5.Imu type, power state            (reads only)
#   t02_still        sensor on; lying flat and still: |a| = 1 g?  noise per axis          (lay it flat on the desk)
#   t03_orientation  4 positions: which axis points where (for "face down = silent" later) (follow the screen)
#   t04_shake        5 s of shaking: peak acceleration and rotation                       (shake it)
#   t05_off          power off again, as the app leaves it; read back
import time
import math
from machine import I2C, Pin

ADDRS = (0x69, 0x68)
REG_CHIP_ID, REG_STATUS, REG_ACC, REG_GYR = 0x00, 0x21, 0x0C, 0x12
REG_ACC_RANGE, REG_PWR_CONF, REG_PWR_CTRL = 0x41, 0x7C, 0x7D
CHIP_ID = 0x24
DEFAULT = ("t01_identify", "t02_still", "t03_orientation", "t04_shake", "t05_off")

_i2c = None
_addr = None


def result(test, status, details=""):
    print("RESULT|%s|%s|%s" % (test, status, details))


def screen(*lines):
    """Show the instruction on the Cardputer (and on the console)."""
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


def countdown(seconds, *lines):
    for s in range(seconds, 0, -1):
        screen(*(lines + ("za %d s" % s,)))
        time.sleep(1)
    screen(*(lines + ("POMIAR - nie ruszaj",)))


def bus():
    global _i2c, _addr
    if _i2c is None:
        _i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
        found = _i2c.scan()
        for a in ADDRS:
            if a in found:
                _addr = a
                break
    return _i2c


def rd(reg, n=1):
    return bus().readfrom_mem(_addr, reg, n)


def wr(reg, value):
    bus().writeto_mem(_addr, reg, bytes([value]))


def _s16(lo, hi):
    v = lo | hi << 8
    return v - 65536 if v & 0x8000 else v


def raw_acc():
    """(x, y, z) in g, read from the registers (independent of M5.Imu)."""
    d = rd(REG_ACC, 6)
    rng = (2, 4, 8, 16)[rd(REG_ACC_RANGE)[0] & 3]
    k = rng / 32768
    return (_s16(d[0], d[1]) * k, _s16(d[2], d[3]) * k, _s16(d[4], d[5]) * k)


def m5_acc():
    import M5
    return tuple(M5.Imu.getAccel())


def m5_gyr():
    import M5
    return tuple(M5.Imu.getGyro())


def mean(samples):
    n = len(samples)
    return tuple(sum(s[i] for s in samples) / n for i in range(3))


def sample(seconds, every_ms=20, source=raw_acc):
    out, end = [], time.ticks_add(time.ticks_ms(), int(seconds * 1000))
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        out.append(source())
        time.sleep_ms(every_ms)
    return out


def norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def fmt(v):
    return "x=%+.2f y=%+.2f z=%+.2f |a|=%.2f" % (v[0], v[1], v[2], norm(v))


def sensor_on():
    wr(REG_PWR_CONF, 0x00)          # advanced power save off
    time.sleep_ms(2)
    wr(REG_PWR_CTRL, 0x0E)          # accelerometer, gyroscope, temperature on
    time.sleep_ms(50)


# ------------------------------------------------------------------------------------------------ tests

def t01_identify():
    bus()
    result("t01_identify", "INFO", "I2C scan %s" % [hex(a) for a in _i2c.scan()])
    if _addr is None:
        result("t01_identify", "FAIL", "no BMI270 at 0x69 / 0x68")
        return False
    cid = rd(REG_CHIP_ID)[0]
    result("t01_identify", "PASS" if cid == CHIP_ID else "FAIL", "chip id 0x%02x at 0x%02x (BMI270 = 0x24)" % (cid, _addr))
    st = rd(REG_STATUS)[0] & 0x0F
    result("t01_identify", "PASS" if st == 1 else "FAIL",
           "INTERNAL_STATUS %d (%s)" % (st, "configuration loaded" if st == 1 else "configuration NOT loaded - needs the 8 KB file"))
    try:
        import M5
        result("t01_identify", "INFO", "M5.Imu type %s, enabled %s" % (M5.Imu.getType(), M5.Imu.isEnabled()))
    except Exception as e:
        result("t01_identify", "INFO", "M5.Imu unavailable: %s" % e)
    result("t01_identify", "INFO", "PWR_CTRL 0x%02x (0x00 = switched off by Squirrel!)" % rd(REG_PWR_CTRL)[0])
    return True


def t02_still():
    if _addr is None and not t01_identify():
        return
    sensor_on()
    countdown(5, "Test 2: spoczynek", "Poloz plasko,", "ekranem do gory")
    s = sample(2)
    m = mean(s)
    noise = tuple(math.sqrt(sum((x[i] - m[i]) ** 2 for x in s) / len(s)) for i in range(3))
    result("t02_still", "PASS" if 0.9 <= norm(m) <= 1.1 else "FAIL", "registers: " + fmt(m))
    result("t02_still", "INFO", "noise (std, g): x=%.4f y=%.4f z=%.4f over %d samples" % (noise + (len(s),)))
    try:
        mm = mean(sample(1, source=m5_acc))
        same = all(abs(mm[i] - m[i]) < 0.1 for i in range(3))
        result("t02_still", "PASS" if same else "FAIL", "M5.Imu.getAccel: " + fmt(mm) + (" (agrees)" if same else " (DIFFERENT axes or scale)"))
    except Exception as e:
        result("t02_still", "INFO", "M5.Imu.getAccel unavailable: %s" % e)
    screen("Test 2: koniec")


POSES = (
    ("screen_up", ("Test 3 (1/4)", "Plasko,", "ekranem do GORY")),
    ("screen_down", ("Test 3 (2/4)", "Plasko,", "ekranem w DOL")),
    ("standing", ("Test 3 (3/4)", "Pionowo, ekran do", "Ciebie, klawiatura", "na dole")),
    ("left_edge", ("Test 3 (4/4)", "Na LEWYM boku", "(ekran do Ciebie)")),
)


def t03_orientation():
    if _addr is None and not t01_identify():
        return
    sensor_on()
    got = {}
    for name, lines in POSES:
        countdown(6, *lines)
        m = mean(sample(1))
        got[name] = m
        axis = max(range(3), key=lambda i: abs(m[i]))
        result("t03_orientation", "INFO", "%-11s %s  -> axis %s%s" % (name, fmt(m), "+" if m[axis] > 0 else "-", "xyz"[axis]))
    up, down = got["screen_up"], got["screen_down"]
    axis = max(range(3), key=lambda i: abs(up[i]))
    ok = abs(up[axis]) > 0.8 and abs(down[axis]) > 0.8 and up[axis] * down[axis] < 0
    result("t03_orientation", "PASS" if ok else "FAIL",
           "face down detectable: axis %s is %+.2f g screen up, %+.2f g screen down" % ("xyz"[axis], up[axis], down[axis]))
    screen("Test 3: koniec")


def t04_shake():
    if _addr is None and not t01_identify():
        return
    sensor_on()
    countdown(4, "Test 4: wstrzas", "Za chwile POTRZASNIJ", "przez 5 sekund")
    screen("Test 4: TRZASNIJ!", "teraz, 5 s")
    peak_a, peak_g, end = 0, 0, time.ticks_add(time.ticks_ms(), 5000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        peak_a = max(peak_a, norm(raw_acc()))
        try:
            peak_g = max(peak_g, norm(m5_gyr()))
        except Exception:
            pass
        time.sleep_ms(10)
    result("t04_shake", "PASS" if peak_a > 2.0 else "FAIL", "peak |a| = %.2f g (shaking should give > 2 g)" % peak_a)
    result("t04_shake", "INFO", "peak rotation %.0f deg/s (M5.Imu.getGyro)" % peak_g)
    screen("Test 4: koniec")


def t05_off():
    if _addr is None and not t01_identify():
        return
    wr(REG_PWR_CTRL, 0x00)
    v = rd(REG_PWR_CTRL)[0]
    result("t05_off", "PASS" if v == 0 else "FAIL", "PWR_CTRL 0x%02x after switching off (as Squirrel! leaves it)" % v)
    screen("Testy akcelerometru", "zakonczone.", "Restart...")


def run(names):
    for name in names or DEFAULT:
        print("\n== " + name)
        try:
            globals()[name]()
        except Exception as e:
            result(name, "FAIL", "%s: %s" % (type(e).__name__, e))
    print("\n== done")
