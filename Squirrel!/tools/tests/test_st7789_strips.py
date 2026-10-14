# tools/tests/test_st7789_strips.py - drivers/st7789_fb.py drawn in strips gives the very picture of the whole buffer
#
# Runs under the MicroPython unix port (framebuf, viper):  <micropython> tools/tests/test_st7789_strips.py
# A fake panel takes what the driver sends (column / row window + pixels); the same drawing - cleared screens,
# transparent and opaque text, shapes, a little drawn later on top - goes to a driver holding the whole panel and to
# one holding 40-row strips, and the two panels must match pixel for pixel.
import sys
sys.path.insert(0, ".")
try:
    import framebuf
except ImportError:
    print("OK (skipped: MicroPython only - framebuf, viper)")
    sys.exit(0)


class FakePort:
    DISPLAY_WIDTH, DISPLAY_HEIGHT = 240, 280


class Panel:
    """ST7789 commands 2A / 2B / 2C over a fake SPI, into a W x H array of 16-bit pixels."""
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 2)
        self.dc = 0
        self.cmd = None
        self.win = (0, 0, w - 1, h - 1)
        self.pos = 0
        self.args = b""

    def pin_dc(self, v=None):
        self.dc = v

    def write(self, data):
        if self.dc == 0:
            self.cmd = data[0]
            self.args = b""
            if self.cmd == 0x2C:
                self.pos = 0
            return
        if self.cmd in (0x2A, 0x2B):
            self.args += bytes(data)
            if len(self.args) == 4:
                a, b = self.args[0] << 8 | self.args[1], self.args[2] << 8 | self.args[3]
                x0, y0, x1, y1 = self.win
                self.win = (a, y0, b, y1) if self.cmd == 0x2A else (x0, a, x1, b)
        elif self.cmd == 0x2C:
            x0, y0, x1, y1 = self.win
            ww = x1 - x0 + 1
            for i in range(0, len(data), 2):
                p = self.pos // 2
                x, y = x0 + p % ww, y0 + p // ww
                if y <= y1:
                    o = (y * self.w + x) * 2
                    self.px[o] = data[i]
                    self.px[o + 1] = data[i + 1]
                self.pos += 2


def make(rows):
    sys.modules["port_config"] = FakePort
    FakePort.DISPLAY_BUFFER_ROWS = rows
    sys.modules.pop("drivers.st7789_fb", None)
    import drivers.st7789_fb as d
    lcd = d.FbLcd()
    panel = Panel(d.W, d.H)
    pin = lambda v=None: None
    lcd.begin(panel, pin, panel.pin_dc, None) if False else None
    lcd._spi, lcd._cs, lcd._dc, lcd._rows = panel, pin, panel.pin_dc, 0
    return lcd, panel


def scene(lcd):
    lcd.fillScreen(0x101010)
    lcd.fillRect(10, 30, 200, 100, 0x2040FF)
    lcd.drawRect(5, 5, 230, 270, 0xFFFFFF)
    lcd.drawLine(0, 0, 239, 279, 0xFF0000)
    lcd.fillCircle(120, 200, 50, 0x00FF00)
    lcd.drawCircle(120, 200, 60, 0xFFFF00)
    lcd.setTextColor(0xFFFFFF, 0x000000)
    lcd.setTextSize(2)
    lcd.drawString("Strips 40-70", 3, 36)           # crosses the strip boundary at 40
    lcd.setTextColor(0xFF8800)                      # transparent
    lcd.setTextSize(3)
    lcd.drawString("over the blue", -8, 75)        # starts left of the panel
    lcd.drawPixel(239, 279, 0xABCDEF)
    lcd.flush()
    lcd.setTextColor(0x00FFFF)                      # drawn later, bit by bit: only that part is sent again
    lcd.setTextSize(1)
    lcd.drawString("later", 100, 118)
    lcd.fillRect(200, 250, 30, 25, 0x777777)
    lcd.flush()


full, panel_full = make(280)
strips, panel_strips = make(40)
ok = not full.strips and strips.strips and len(strips.buf) == 240 * 40 * 2
scene(full)
scene(strips)
same = panel_full.px == panel_strips.px
diff = sum(1 for i in range(0, len(panel_full.px), 2) if panel_full.px[i:i + 2] != panel_strips.px[i:i + 2]) if not same else 0
print("modes ok" if ok else "FAIL modes", "| identical" if same else "| FAIL %d pixels differ" % diff)
lcd2, _p = make(40)
for k in range(2000):
    lcd2.drawPixel(k % 240, 5, 0xFFFFFF)
print("ops kept bounded:", len(lcd2._ops) <= 600)
print("OK" if ok and same and len(lcd2._ops) <= 600 else "FAILED")
