# machine.py - fake ESP32 peripherals: pins, an I2C bus with a TCA8418 keyboard on it, the RTC
import sim_state as _s

_freq = [240000000]


def freq(hz=None):
    if hz is None:
        return _freq[0]
    _freq[0] = hz


def reset_cause():
    return 1


def reset():
    raise SystemExit("machine.reset()")


def soft_reset():
    raise SystemExit("machine.soft_reset()")


def lightsleep(ms=0):
    _s.ms += ms


deepsleep = lightsleep


def idle():
    pass


def unique_id():
    return b"\x01\x02\x03\x04\x05\x06"


def bitstream(*a):
    pass


SLEEP = 2
DEEPSLEEP = 4


class Pin:
    IN, OUT, OPEN_DRAIN = 1, 3, 7
    PULL_UP, PULL_DOWN = 1, 2
    IRQ_FALLING, IRQ_RISING, IRQ_LOW_LEVEL, IRQ_HIGH_LEVEL = 2, 1, 4, 5

    def __init__(self, num, mode=-1, pull=-1, value=None, **k):
        self.num = num
        self._v = 0 if value is None else value

    def init(self, *a, **k):
        if "value" in k:
            self._v = k["value"]

    def value(self, v=None):
        if v is None:
            if self.num == 0:
                return _s.button0
            return self._v
        self._v = v

    def on(self):
        self._v = 1

    def off(self):
        self._v = 0

    def __call__(self, v=None):
        return self.value(v)

    def irq(self, *a, **k):
        pass


class Signal(Pin):
    pass


class PWM:
    def __init__(self, pin, freq=0, duty_u16=0, **k):
        self._d = duty_u16

    def duty_u16(self, v=None):
        if v is None:
            return self._d
        self._d = v

    def freq(self, v=None):
        return 0

    def deinit(self):
        pass


class _TCA8418:
    def __init__(self):
        self.regs = {0x01: 0x00, 0x1D: 0x00, 0x1E: 0x00, 0x1F: 0x00, 0x02: 0}

    def read(self, reg):
        if reg == 0x04:
            return _s.keys.pop(0) if _s.keys else 0
        return self.regs.get(reg, 0)

    def write(self, reg, data):
        self.regs[reg] = data[0]


_DEVICES = {0x34: _TCA8418()}


class I2C:
    def __init__(self, *a, **k):
        pass

    def scan(self):
        return sorted(_DEVICES)

    def readfrom_mem(self, addr, reg, n, **k):
        dev = _DEVICES.get(addr)
        if dev is None:
            raise OSError(19)
        return bytes([dev.read(reg)] + [0] * (n - 1))

    def writeto_mem(self, addr, reg, data, **k):
        dev = _DEVICES.get(addr)
        if dev is None:
            raise OSError(19)
        dev.write(reg, data)

    def readfrom(self, addr, n, *a):
        raise OSError(19)

    def writeto(self, addr, data, *a):
        raise OSError(19)


SoftI2C = I2C


class RTC:
    def datetime(self, t=None):
        import time
        if t is None:
            y, m, d, h, mi, s, wd, yd = time.localtime()
            return (y, m, d, wd, h, mi, s, 0)
        y, m, d, wd, h, mi, s = t[:7]
        _s.wall_s = time.mktime((y, m, d, h, mi, s, 0, 0)) - _s.ms // 1000

    def init(self, t):
        self.datetime(t)


class SDCard:
    def __init__(self, **k):
        pass

    def deinit(self):
        pass


class ADC:
    def __init__(self, *a, **k):
        pass

    def read_u16(self):
        return 30000

    def read_uv(self):
        return 1500000


class SPI:
    def __init__(self, *a, **k):
        pass

    def write(self, *a):
        pass


class Timer:
    def __init__(self, *a, **k):
        pass

    def init(self, *a, **k):
        pass

    def deinit(self):
        pass


class WDT:
    def __init__(self, *a, **k):
        pass

    def feed(self):
        pass
