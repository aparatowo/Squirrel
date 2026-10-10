# twatch_screen.py - the T-Watch display for the test scripts: instructions, big digits (put in front of a script by
# run.py through  # INCLUDE: twatch_screen.py).  Confirmed on the watch on 2026-10-10: ST7789 240x240, MADCTL 0xC0 with a
# row offset of 80 (rotated 180 degrees: the panel's RAM has 320 rows), colour inversion on, SPI mode 0 at 26.67 MHz,
# backlight GPIO15, panel and backlight powered by the AXP202's LDO2.  Text: MicroPython's built-in 8x8 font, scaled up
# (ASCII only - no Polish letters).
import struct
import framebuf
from machine import I2C, Pin

TFT_SCK, TFT_MOSI, TFT_CS, TFT_DC, TFT_BL = 18, 19, 5, 27, 15
W = H = 240
BLACK, WHITE, RED, GREEN, BLUE = 0x0000, 0xFFFF, 0xF800, 0x07E0, 0x001F
YELLOW, CYAN, ORANGE, GRAY = 0xFFE0, 0x07FF, 0xFD20, 0x8410

_spi = None
_screen = None


def display_spi():
    """The display's SPI bus, created once.  26.67 MHz is the most the ESP32 gives on pins routed through its GPIO
    matrix (MOSI is GPIO19, not the bus's native pin): at 40 MHz MicroPython 1.25 panics instead of raising.  MISO is not
    wired: miso=None (else SPI(2) puts its default MISO on GPIO19 - our MOSI)."""
    global _spi
    if _spi is None:
        from machine import SPI
        _spi = SPI(2, baudrate=26666666, polarity=0, phase=0, sck=Pin(TFT_SCK), mosi=Pin(TFT_MOSI), miso=None)
    return _spi


def _ldo2_on():
    """Panel and backlight power: AXP202 LDO2, only when it is set to 3.0-3.3 V (register 0x28)."""
    i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=400000)
    volts = 1.8 + 0.1 * (i2c.readfrom_mem(0x35, 0x28, 1)[0] >> 4)
    if not 3.0 <= volts <= 3.31:
        raise RuntimeError("LDO2 is set to %.2f V - display not powered" % volts)
    out = i2c.readfrom_mem(0x35, 0x12, 1)[0]
    if not out & 0x04:
        i2c.writeto_mem(0x35, 0x12, bytes([out | 0x04]))


class Screen:
    def __init__(self, madctl=0xC0, row_offset=80):
        _ldo2_on()
        self.spi = display_spi()
        self.cs = Pin(TFT_CS, Pin.OUT, value=1)
        self.dc = Pin(TFT_DC, Pin.OUT, value=1)
        self.rows = row_offset
        for cmd, data, wait in ((0x01, b"", 150), (0x11, b"", 120), (0x3A, b"\x55", 10), (0x36, bytes([madctl]), 0),
                                (0x21, b"", 0), (0x13, b"", 10), (0x29, b"", 50)):
            self.cmd(cmd, data)
            sleep_ms(wait)
        Pin(TFT_BL, Pin.OUT, value=1)

    def cmd(self, c, data=b""):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([c]))
        if data:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)

    def _window(self, x, y, w, h):
        self.cmd(0x2A, struct.pack(">HH", x, x + w - 1))
        self.cmd(0x2B, struct.pack(">HH", y + self.rows, y + self.rows + h - 1))
        self.cs(0)
        self.dc(0)
        self.spi.write(b"\x2c")
        self.dc(1)

    def rect(self, x, y, w, h, color):
        self._window(x, y, w, h)
        line = struct.pack(">H", color) * w
        for _ in range(h):
            self.spi.write(line)
        self.cs(1)

    def blit(self, x, y, w, h, data):
        self._window(x, y, w, h)
        self.spi.write(data)
        self.cs(1)

    def clear(self, color=BLACK):
        self.rect(0, 0, W, H, color)

    def text(self, s, x, y, scale=3, fg=WHITE, bg=BLACK):
        """Draw `s` (ASCII) with its top left corner at x, y; returns the width in pixels.  x = None: centred."""
        w = 8 * len(s)
        if not w:
            return 0
        fb = framebuf.FrameBuffer(bytearray(((w + 7) // 8) * 8), w, 8, framebuf.MONO_HLSB)
        fb.text(s, 0, 0, 1)
        if x is None:
            x = max(0, (W - w * scale) // 2)
        on, off = struct.pack(">H", fg) * scale, struct.pack(">H", bg) * scale
        out = bytearray()
        for row in range(8):
            line = b"".join(on if fb.pixel(col, row) else off for col in range(w))
            out += line * scale
        self.blit(x, y, w * scale, 8 * scale, out)
        return w * scale

    def lines(self, rows, color=WHITE, scale=3, top=None):
        """An instruction screen: the lines centred, one under the other."""
        self.clear()
        step = 8 * scale + 6
        y = top if top is not None else max(0, (H - step * len(rows)) // 2)
        for r in rows:
            fg = color
            if isinstance(r, tuple):
                r, fg = r
            self.text(r, None, y, scale, fg)
            y += step

    BIG = 8                                    # digits: 64 x 64 pixels
    MARGIN = 8

    def spot(self, where):
        """The top left corner of a 64 x 64 target at "TL", "TR", "BL", "BR" or "C"."""
        big, m = 8 * self.BIG, self.MARGIN
        return {"TL": (m, m), "TR": (W - m - big, m), "BL": (m, H - m - big), "BR": (W - m - big, H - m - big),
                "C": ((W - big) // 2, (H - big) // 2)}[where]

    def digit(self, ch, where, color=YELLOW):
        x, y = self.spot(where)
        self.text(ch, x, y, self.BIG, color)
        return x + 4 * self.BIG, y + 4 * self.BIG             # the target's centre


def screen():
    global _screen
    if _screen is None:
        _screen = Screen()
    return _screen


def sleep_ms(ms):
    import time
    time.sleep_ms(ms)
