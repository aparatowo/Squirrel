# st7789_fb.py - an ST7789 display drawn through a frame buffer in RAM (the T-Watch 2020's 240x240 panel)
#
# The app draws with the calls of M5.Lcd (fillRect, drawString with a text size, setTextColor ...).  Here they go into a
# W x H RGB565 buffer (240 x 240: 115 KB - it needs PSRAM) with framebuf (C) and viper (native code); flush() sends only the rectangle that
# changed since the last flush.  Nothing flickers (the screen is complete before it is sent) and little is sent: one
# changed clock digit is 6 KB, the whole screen 115 KB (40 ms over SPI).  Measured on the watch (tools/hwtest/
# twatch_gfx_bench.py): a menu screen ~85 ms, 13 lines of text ~125 ms, a clock digit ~10 ms (160 MHz).
#
# Colours come as 0xRRGGBB (like M5.Lcd) and are stored as RGB565 with the bytes swapped, so the buffer is already in
# the panel's byte order.  Text: the 'classic' 5x7 font of Adafruit GFX (drivers/glcdfont.py) - the very font M5GFX uses
# by default - so setTextSize(n) gives 6n x 8n pixels per character, as on the Cardputer, and layouts made for M5.Lcd
# fit.  Each glyph is scaled once into a cached 1-bit mask and drawn by viper.
#
# The layout area: the app may be given a layout height smaller than the panel (set_layout; [display] layout_height):
# its drawing is then centred vertically, and fillScreen still clears the whole panel.  So screens laid out for the
# Cardputer's 240 x 135 show as they are, until they are made for the full height.
#
# `lcd` exists from import on (gfx.py takes it then), but touches no hardware: the board powers the panel first and
# then calls lcd.begin(...).  Until then drawing only fills the buffer.
import struct
import framebuf
import micropython
from drivers.glcdfont import FONT
from drivers.glcdfont_latin import CHARS as _LATIN, DATA as _LATIN_DATA

try:                                       # the panel's size: [display] width / height of the port
    import port_config as _pc
    W, H = getattr(_pc, "DISPLAY_WIDTH", 240), getattr(_pc, "DISPLAY_HEIGHT", 240)
except ImportError:
    _pc = None
    W = H = 240
_STRIP_ROWS = 40                           # strips: 240 x 40 = 19 KB, when the whole panel is too big for the heap
_MAX_OPS = 600                             # strips: a screen drawn bit by bit for so long is redrawn from a clean list


def _swap565(c):
    """0xRRGGBB -> RGB565, bytes swapped (framebuf keeps pixels little-endian, the panel wants big-endian)."""
    v = (c >> 8 & 0xF800) | (c >> 5 & 0x07E0) | (c >> 3 & 0x001F)
    return (v >> 8 | v << 8) & 0xFFFF


@micropython.viper
def _glyph(buf: ptr16, bw: int, x: int, y: int, mask: ptr8, w: int, h: int, stride: int, fg: int, bg: int):
    """Write a w x h 1-bit glyph (rows of `stride` bytes) into the RGB565 buffer at x, y."""
    row = 0
    while row < h:
        p = (y + row) * bw + x
        m = row * stride
        col = 0
        while col < w:
            if (mask[m + (col >> 3)] >> (7 - (col & 7))) & 1:
                buf[p + col] = fg
            else:
                buf[p + col] = bg
            col += 1
        row += 1


@micropython.viper
def _gather(dst: ptr8, src: ptr8, bw2: int, x2: int, w2: int, y0: int, rows: int):
    """Copy `rows` rows of w2 bytes (from row y0, byte column x2 of the screen buffer) into dst, one after the other."""
    r = 0
    o = 0
    while r < rows:
        a = (y0 + r) * bw2 + x2
        i = 0
        while i < w2:
            dst[o] = src[a + i]
            i += 1
            o += 1
        r += 1


class FbLcd:
    glyphs = _LATIN                        # gfx.py: letters beyond ASCII this driver draws itself (not folded)

    """The panel in a frame buffer.  Two ways to hold it:
    the whole panel (PSRAM; W x H x 2 bytes) - every call draws into it at once, flush() sends what changed;
    strips (no room for that: a module without PSRAM, or [display] buffer_rows) - the calls are kept as a list since
    the screen was last cleared, and flush() replays them into a strip of rows at a time (only the calls that reach
    that strip), sending each strip's part of what changed.  Slower (a call reaching two strips is drawn twice), but
    the result is the same - transparent text and drawing bit by bit included - in 19 KB instead of 115-134 KB."""
    font_active = False                    # gfx.py: no .vlw fonts here (setFont raises)
    _needs_flush = True                    # gfx.py: what is drawn shows on flush() only
    _can_layout = True                     # gfx.py: the layout area can change (a touch screen may use the full height)

    def __init__(self):
        rows = getattr(_pc, "DISPLAY_BUFFER_ROWS", None)
        if rows is None:                   # the whole panel only where it is a small part of the heap (PSRAM): taking
            try:                           # 115-134 KB of an S3's internal RAM would leave Wi-Fi / Bluetooth without
                import gc
                heap = gc.mem_free() + gc.mem_alloc()
            except (ImportError, AttributeError):
                heap = 1 << 30
            rows = H if W * H * 2 <= heap // 4 else _STRIP_ROWS
        rows = min(H, rows)
        try:
            self.buf = bytearray(W * rows * 2)
        except MemoryError:
            rows = _STRIP_ROWS
            self.buf = bytearray(W * rows * 2)
        self._bh = rows                    # rows the buffer holds
        self._by = 0                       # the panel row the buffer starts at (strips: the strip being drawn)
        self._ops = None if rows >= H else []
        self.mv = memoryview(self.buf)
        self.fb = framebuf.FrameBuffer(self.buf, W, rows, framebuf.RGB565)
        self._row = bytearray(W * 2 * 40)  # rows gathered for one SPI write
        self._fg, self._bg, self._size = 0xFFFF, 0x0000, 1
        self._masks = {}
        self._pal = framebuf.FrameBuffer(bytearray(4), 2, 1, framebuf.RGB565)
        self.dirty = None                  # [x0, y0, x1, y1] (inclusive) or None
        self._spi = None                   # set by begin()
        self._bright = 255
        self._pwm = None
        self._oy = 0                       # where the layout area starts (set_layout)
        self._lh = H                       # its height

    @property
    def strips(self):
        return self._ops is not None

    # ------------------------------------------------------------------ the panel

    def begin(self, spi, cs, dc, backlight, madctl=0x00, row_offset=0):
        """Initialise the panel (powered by now) and show the buffer.  spi: a machine.SPI; cs, dc: machine.Pin;
        backlight: a machine.PWM on the backlight pin."""
        import time
        self._spi, self._cs, self._dc, self._rows = spi, cs, dc, row_offset
        for cmd, data, wait in ((0x01, b"", 150), (0x11, b"", 120), (0x3A, b"\x55", 10), (0x36, bytes([madctl]), 0),
                                (0x21, b"", 0), (0x13, b"", 10), (0x29, b"", 50)):
            self._cmd(cmd, data)
            time.sleep_ms(wait)
        self._pwm = backlight
        self.setBrightness(self._bright)
        self.dirty = [0, 0, W - 1, H - 1]
        self.flush()

    def set_layout(self, height):
        """The app lays its screens out on W x height, shown centred vertically on the panel."""
        self._lh = min(H, height)
        self._oy = (H - self._lh) // 2

    def layout_origin(self):
        """Where the layout area starts on the panel (the touch layer subtracts it)."""
        return self._oy

    def sleep(self):
        """The panel off and asleep (before a deep sleep; begin() wakes it again after the restart)."""
        if self._spi is not None:
            self.setBrightness(0)
            self._cmd(0x28)                    # display off
            self._cmd(0x10)                    # sleep in

    def _cmd(self, c, data=b""):
        self._cs(0)
        self._dc(0)
        self._spi.write(bytes([c]))
        if data:
            self._dc(1)
            self._spi.write(data)
        self._cs(1)

    def flush(self):
        """Send the rectangle changed since the last flush.  Returns the bytes sent."""
        d = self.dirty
        if d is None or self._spi is None:
            return 0
        self.dirty = None
        x0, y0, x1, y1 = d
        if self._ops is None:
            self._send(x0, y0, x1, y1)
            return (x1 - x0 + 1) * (y1 - y0 + 1) * 2
        bh = self._bh
        top = y0 - y0 % bh
        while top <= y1:
            self._by = top
            bottom = top + bh - 1
            for op in self._ops:
                if op[2] <= bottom and op[4] >= top and op[1] <= x1 and op[3] >= x0:
                    self._exec(op)
            self._send(x0, max(y0, top), x1, min(y1, bottom))
            top += bh
        self._by = 0
        return (x1 - x0 + 1) * (y1 - y0 + 1) * 2

    def _send(self, x0, y0, x1, y1):
        """Panel rows y0..y1, columns x0..x1, from the buffer (which starts at panel row self._by)."""
        w, h = x1 - x0 + 1, y1 - y0 + 1
        self._cmd(0x2A, struct.pack(">HH", x0, x1))
        self._cmd(0x2B, struct.pack(">HH", y0 + self._rows, y1 + self._rows))
        self._cs(0)
        self._dc(0)
        self._spi.write(b"\x2c")
        self._dc(1)
        b0 = y0 - self._by
        if w == W:
            self._spi.write(self.mv[b0 * W * 2:(b0 + h) * W * 2])
        else:
            rows = len(self._row) // (w * 2)
            strip = memoryview(self._row)
            y = b0
            while y < b0 + h:
                k = min(rows, b0 + h - y)
                _gather(self._row, self.buf, W * 2, x0 * 2, w * 2, y, k)
                self._spi.write(strip[:k * w * 2])
                y += k
        self._cs(1)

    def _mark(self, x, y, w, h):
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W - 1, x + w - 1), min(H - 1, y + h - 1)
        if x1 < x0 or y1 < y0:
            return
        d = self.dirty
        if d is None:
            self.dirty = [x0, y0, x1, y1]
        else:
            if x0 < d[0]: d[0] = x0
            if y0 < d[1]: d[1] = y0
            if x1 > d[2]: d[2] = x1
            if y1 > d[3]: d[3] = y1

    # ------------------------------------------------------------------ drawing: now, or kept for the strips

    def _draw(self, op):
        """op = (kind, x0, y0, x1, y1 (the panel rectangle it reaches, inclusive), arguments ...)."""
        self._mark(op[1], op[2], op[3] - op[1] + 1, op[4] - op[2] + 1)
        if self._ops is None:
            self._exec(op)
            return
        if op[0] == "fill" or (op[0] == "frect" and op[1] <= 0 and op[2] <= 0 and op[3] >= W - 1 and op[4] >= H - 1):
            self._ops = []                         # the whole panel covered: what was under it does not count
        elif len(self._ops) >= _MAX_OPS:
            self._ops = self._ops[len(self._ops) // 2:]     # a screen drawn bit by bit for very long: keep the newer half
        self._ops.append(op)

    def _exec(self, op):
        kind, dy, fb = op[0], -self._by, self.fb
        if kind == "frect":
            fb.fill_rect(op[5], op[6] + dy, op[7], op[8], op[9])
        elif kind == "text":
            self._text(op[5], op[6], op[7] + dy, op[8], op[9], op[10])
        elif kind == "fill":
            fb.fill(op[5])
        elif kind == "rect":
            fb.rect(op[5], op[6] + dy, op[7], op[8], op[9])
        elif kind == "line":
            fb.line(op[5], op[6] + dy, op[7], op[8] + dy, op[9])
        elif kind == "px":
            fb.pixel(op[5], op[6] + dy, op[7])
        elif kind == "circ":
            fb.ellipse(op[5], op[6] + dy, op[7], op[7], op[8], op[9])

    # ------------------------------------------------------------------ the calls of M5.Lcd

    def width(self):
        return W

    def height(self):
        return self._lh

    def fillScreen(self, c):
        self._draw(("fill", 0, 0, W - 1, H - 1, _swap565(c)))   # the whole panel, the bands around the layout area too

    def fillRect(self, x, y, w, h, c):
        y += self._oy
        self._draw(("frect", x, y, x + w - 1, y + h - 1, x, y, w, h, _swap565(c)))

    def drawRect(self, x, y, w, h, c):
        y += self._oy
        self._draw(("rect", x, y, x + w - 1, y + h - 1, x, y, w, h, _swap565(c)))

    def drawLine(self, x0, y0, x1, y1, c):
        y0 += self._oy
        y1 += self._oy
        self._draw(("line", min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), x0, y0, x1, y1, _swap565(c)))

    def drawPixel(self, x, y, c):
        y += self._oy
        self._draw(("px", x, y, x, y, x, y, _swap565(c)))

    def fillCircle(self, x, y, r, c):
        y += self._oy
        self._draw(("circ", x - r, y - r, x + r, y + r, x, y, r, _swap565(c), True))

    def drawCircle(self, x, y, r, c):
        y += self._oy
        self._draw(("circ", x - r, y - r, x + r, y + r, x, y, r, _swap565(c), False))

    def setTextColor(self, fg, bg=None):
        self._fg = _swap565(fg)
        self._bg = None if bg is None else _swap565(bg)

    def setTextSize(self, n):
        self._size = max(1, int(n))

    def textWidth(self, s):
        return 6 * self._size * len(s)

    def fontHeight(self, *a):
        return 8 * self._size

    def setFont(self, *a):
        raise OSError("st7789_fb: no .vlw fonts")

    def setBrightness(self, v):
        self._bright = max(0, min(255, int(v)))
        if self._pwm is not None:
            self._pwm.duty_u16(self._bright * 257)

    def getBrightness(self):
        return self._bright

    def _mask(self, ch, size):
        """The glyph `ch` (glcdfont: 5 columns + 1 blank, 8 rows) scaled `size` times, as rows of whole bytes (MSB
        first) - built once, then cached."""
        key = (ch, size)
        m = self._masks.get(key)
        if m is not None:
            return m
        code = ord(ch)
        font, base = FONT, 5 * code
        if code > 127:                                    # the font's 128-255 are CP437 symbols, not Latin-1:
            i = _LATIN.find(ch)                           # the accented letters have glyphs of their own
            font, base = (_LATIN_DATA, 5 * i) if i >= 0 else (FONT, 5 * 0x3F)     # anything else: '?'
        w = 6 * size
        stride = (w + 7) // 8
        m = bytearray(stride * 8 * size)
        for xx in range(5):
            column = font[base + xx]
            for yy in range(8):
                if column >> yy & 1:
                    for dy in range(size):
                        row = (yy * size + dy) * stride
                        for dx in range(size):
                            col = xx * size + dx
                            m[row + (col >> 3)] |= 0x80 >> (col & 7)
        self._masks[key] = m
        return m

    def drawString(self, s, x, y, *rest):
        size = self._size
        y += self._oy
        right = min(W, x + 6 * size * len(s))
        self._draw(("text", x, y, right - 1, y + 8 * size - 1, s, x, y, self._fg, self._bg, size))

    def _text(self, s, x, y, fg, bg, size):
        """The text into the buffer: y in the buffer's rows (the panel's, less the strip's start)."""
        w, h = 6 * size, 8 * size
        stride = (w + 7) // 8
        buf, rows = self.buf, self._bh
        cx = x
        for ch in s:
            if cx >= W:
                break
            if bg is not None and cx >= 0 and cx + w <= W and 0 <= y and y + h <= rows:
                _glyph(buf, W, cx, y, self._mask(ch, size), w, h, stride, fg, bg)
            elif -h < y < rows:                       # transparent, or cut by an edge: framebuf clips
                g = framebuf.FrameBuffer(self._mask(ch, size), w, h, framebuf.MONO_HLSB)
                pal = self._pal
                pal.pixel(1, 0, fg)
                key = (fg ^ 1) if bg is None else -1     # framebuf compares the key AFTER the palette: never the fg
                pal.pixel(0, 0, key if bg is None else bg)
                self.fb.blit(g, cx, y, key, pal)
            cx += w


lcd = FbLcd()
