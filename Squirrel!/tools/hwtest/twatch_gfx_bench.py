# EXPECT_MACHINE: SPIRAM with ESP32
# SERIAL_LINES: low
# USB_VENDOR: 1a86
# INCLUDE: twatch_screen.py
# twatch_gfx_bench.py - how fast can the watch draw Squirrel!-like screens with MicroPython's framebuf (no C module)?
#
# FbDisplay is a prototype of the watch's display driver: the calls of M5.Lcd the app uses (fillScreen, fillRect,
# drawString with a text size ...), drawn by framebuf (C) into a 240x240 RGB565 buffer in PSRAM, and flush() sends
# only the rectangle that changed.  Colours are stored byte-swapped, so the buffer is already in the panel's byte order.
# Text: the built-in 8x8 font; each glyph is scaled once into a cached 1-bit bitmap, then drawn with framebuf.blit and
# a 2-colour palette (C speed).
#
#   t01_menu      a menu screen: header, 5 rows, a highlighted row - drawn and flushed in full; then moving the highlight
#   t02_clock     the clock: big 7-segment digits; one minute changes - only that digit is flushed
#   t03_text      a note viewer: 13 lines of text, full redraw
#   t04_full      sending the whole buffer (the floor of any full redraw)
import time
import struct
import framebuf

DEFAULT = ("t04_full", "t01_menu", "t02_clock", "t03_text", "t05_fast", "t06_viper")


def result(test, status, details=""):
    print("RESULT|%s|%s|%s" % (test, status, details))


def swap(c):
    """0xRRGGBB (as the app gives colours, M5.Lcd style) -> RGB565 with the bytes swapped for framebuf."""
    v = (c >> 8 & 0xF800) | (c >> 5 & 0x07E0) | (c >> 3 & 0x001F)
    return (v >> 8 | v << 8) & 0xFFFF


class FbDisplay:
    def __init__(self, scr):
        self.scr = scr
        self.buf = bytearray(W * H * 2)
        self.mv = memoryview(self.buf)
        self.fb = framebuf.FrameBuffer(self.buf, W, H, framebuf.RGB565)
        self._fg, self._bg, self._size = 0xFFFF, 0x0000, 1
        self._glyphs = {}
        self._pal = framebuf.FrameBuffer(bytearray(4), 2, 1, framebuf.RGB565)
        self.dirty = None                     # [x0, y0, x1, y1] (inclusive) or None
        self.fast = False                     # colour glyph cache + one-write flush (t05_fast)
        self._row = bytearray(W * 2 * 40)     # a strip of rows gathered for one SPI write

    # ---- dirty rectangle
    def _mark(self, x, y, w, h):
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W - 1, x + w - 1), min(H - 1, y + h - 1)
        if x1 < x0 or y1 < y0:
            return
        d = self.dirty
        if d is None:
            self.dirty = [x0, y0, x1, y1]
        else:
            d[0], d[1], d[2], d[3] = min(d[0], x0), min(d[1], y0), max(d[2], x1), max(d[3], y1)

    def flush(self):
        """Send the changed rectangle to the panel; returns the bytes sent."""
        d = self.dirty
        if d is None:
            return 0
        self.dirty = None
        x0, y0, x1, y1 = d
        w, h = x1 - x0 + 1, y1 - y0 + 1
        scr = self.scr
        scr._window(x0, y0, w, h)
        if w == W:
            scr.spi.write(self.mv[y0 * W * 2:(y1 + 1) * W * 2])
        elif self.fast:
            rows = len(self._row) // (w * 2)          # gather as many rows as fit, then one write
            strip = memoryview(self._row)
            y = y0
            while y <= y1:
                k = min(rows, y1 - y + 1)
                for i in range(k):
                    a = ((y + i) * W + x0) * 2
                    strip[i * w * 2:(i + 1) * w * 2] = self.mv[a:a + w * 2]
                scr.spi.write(strip[:k * w * 2])
                y += k
        else:
            for y in range(y0, y1 + 1):
                a = (y * W + x0) * 2
                scr.spi.write(self.mv[a:a + w * 2])
        scr.cs(1)
        return w * h * 2

    # ---- the M5.Lcd calls the app uses
    def fillScreen(self, c):
        self.fb.fill(swap(c))
        self._mark(0, 0, W, H)

    def fillRect(self, x, y, w, h, c):
        self.fb.fill_rect(x, y, w, h, swap(c))
        self._mark(x, y, w, h)

    def drawRect(self, x, y, w, h, c):
        self.fb.rect(x, y, w, h, swap(c))
        self._mark(x, y, w, h)

    def drawLine(self, x0, y0, x1, y1, c):
        self.fb.line(x0, y0, x1, y1, swap(c))
        self._mark(min(x0, x1), min(y0, y1), abs(x1 - x0) + 1, abs(y1 - y0) + 1)

    def fillCircle(self, x, y, r, c):
        self.fb.ellipse(x, y, r, r, swap(c), True)
        self._mark(x - r, y - r, 2 * r + 1, 2 * r + 1)

    def setTextColor(self, fg, bg=None):
        self._fg = swap(fg)
        self._bg = swap(bg) if bg is not None else None

    def setTextSize(self, n):
        self._size = n

    def textWidth(self, s):
        return 8 * self._size * len(s)

    def _glyph(self, ch, size):
        key = ch + chr(size)
        g = self._glyphs.get(key)
        if g is None:
            src = framebuf.FrameBuffer(bytearray(8), 8, 8, framebuf.MONO_HLSB)
            src.text(ch, 0, 0, 1)
            n = 8 * size
            g = framebuf.FrameBuffer(bytearray(((n + 7) // 8) * n), n, n, framebuf.MONO_HLSB)
            for yy in range(8):
                for xx in range(8):
                    if src.pixel(xx, yy):
                        g.fill_rect(xx * size, yy * size, size, size, 1)
            self._glyphs[key] = g
        return g

    def _cglyph(self, ch, size, fg, bg):
        """The glyph already in its colours (RGB565, swapped): blit without a palette."""
        key = (ch, size, fg, bg)
        g = self._glyphs.get(key)
        if g is None:
            m = self._glyph(ch, size)
            n = 8 * size
            g = framebuf.FrameBuffer(bytearray(n * n * 2), n, n, framebuf.RGB565)
            g.fill(bg)
            pal = framebuf.FrameBuffer(bytearray(4), 2, 1, framebuf.RGB565)
            pal.pixel(0, 0, bg)
            pal.pixel(1, 0, fg)
            g.blit(m, 0, 0, -1, pal)
            self._glyphs[key] = g
        return g

    def drawString(self, s, x, y):
        n = 8 * self._size
        if self.fast and self._bg is not None:
            fb, size, fg, bg = self.fb, self._size, self._fg, self._bg
            cx = x
            for ch in s:
                fb.blit(self._cglyph(ch, size, fg, bg), cx, y)
                cx += n
            self._mark(x, y, cx - x, n)
            return
        pal = self._pal
        pal.pixel(1, 0, self._fg)
        if self._bg is None:
            key = 0
            pal.pixel(0, 0, 0)
        else:
            key = -1
            pal.pixel(0, 0, self._bg)
        fb = self.fb
        cx = x
        for ch in s:
            fb.blit(self._glyph(ch, self._size), cx, y, key, pal)
            cx += n
        self._mark(x, y, cx - x, n)


_disp = None


def disp():
    global _disp
    if _disp is None:
        _disp = FbDisplay(screen())
    return _disp


def timed(fn):
    t = time.ticks_us()
    out = fn()
    return time.ticks_diff(time.ticks_us(), t) / 1000, out


ORANGE_, GREEN_, BLACK_, DARK_, YELLOW_ = 0xFFA500, 0x00FF00, 0x000000, 0x444444, 0xFFFF00
MENU = ("1. Focus Tools", "2. Notes", "3. To-Do List", "4. Settings", "5. Statistics")


def draw_menu(d, selected):
    d.fillScreen(BLACK_)
    d.setTextSize(2)
    d.setTextColor(ORANGE_, BLACK_)
    d.drawString("# Squirrel #", 24, 12)
    d.drawLine(0, 36, 239, 36, ORANGE_)
    for i, label in enumerate(MENU):
        y = 52 + i * 34
        if i == selected:
            d.fillRect(0, y - 6, 240, 28, DARK_)
            d.setTextColor(GREEN_, DARK_)
        else:
            d.setTextColor(ORANGE_, BLACK_)
        d.drawString(label, 8, y)


def t04_full():
    d = disp()
    d.fillScreen(0x000000)
    ms, sent = timed(d.flush)
    result("t04_full", "INFO", "whole buffer %d bytes sent in %.1f ms" % (sent, ms))


def t01_menu():
    d = disp()
    first, _ = timed(lambda: draw_menu(d, 0))            # includes building the glyph cache
    again, _ = timed(lambda: draw_menu(d, 0))            # glyphs cached
    fl, sent = timed(d.flush)
    result("t01_menu", "INFO", "menu drawn: %.1f ms the first time (glyph cache), %.1f ms after; flush %d B in %.1f ms" % (first, again, sent, fl))
    time.sleep_ms(800)
    # moving the highlight: only the two rows change (the app redraws the screen; a smarter app redraws only them)
    def move():
        y_old, y_new = 52 - 6, 52 + 34 - 6
        d.fillRect(0, y_old, 240, 28, BLACK_)
        d.setTextColor(ORANGE_, BLACK_)
        d.drawString(MENU[0], 8, 52)
        d.fillRect(0, y_new, 240, 28, DARK_)
        d.setTextColor(GREEN_, DARK_)
        d.drawString(MENU[1], 8, 52 + 34)
    dr, _ = timed(move)
    fl2, sent2 = timed(d.flush)
    result("t01_menu", "INFO", "highlight moved (2 rows): draw %.1f ms, flush %d B in %.1f ms -> %.1f ms in all" % (dr, sent2, fl2, dr + fl2))
    full, _ = timed(lambda: (draw_menu(d, 2), d.flush()))
    result("t01_menu", "PASS" if full < 150 else "INFO", "full menu redraw + flush: %.1f ms (under 150 ms feels instant)" % full)
    time.sleep_ms(800)


SEG = {'0': (1,1,1,0,1,1,1), '1': (0,0,1,0,0,1,0), '2': (1,0,1,1,1,0,1), '3': (1,0,1,1,0,1,1), '4': (0,1,1,1,0,1,0),
       '5': (1,1,0,1,0,1,1), '6': (1,1,0,1,1,1,1), '7': (1,0,1,0,0,1,0), '8': (1,1,1,1,1,1,1), '9': (1,1,1,1,0,1,1)}


def digit(d, x, y, ch, w=40, h=80, t=8, c=ORANGE_):
    """The 7-segment digit of ui_renderer.py, larger."""
    d.fillRect(x, y, w, h, BLACK_)
    s = SEG[ch]
    hh = h // 2
    if s[0]: d.fillRect(x, y, w, t, c)
    if s[1]: d.fillRect(x, y, t, hh, c)
    if s[2]: d.fillRect(x + w - t, y, t, hh, c)
    if s[3]: d.fillRect(x, y + hh - t // 2, w, t, c)
    if s[4]: d.fillRect(x, y + hh, t, hh, c)
    if s[5]: d.fillRect(x + w - t, y + hh, t, hh, c)
    if s[6]: d.fillRect(x, y + h - t, w, t, c)


def draw_clock(d, hhmm):
    xs = (14, 64, 136, 186)
    for i, ch in enumerate(hhmm.replace(":", "")):
        digit(d, xs[i], 70, ch)
    d.fillRect(116, 92, 8, 8, ORANGE_)
    d.fillRect(116, 128, 8, 8, ORANGE_)


def t02_clock():
    d = disp()
    d.fillScreen(BLACK_)
    draw_clock(d, "12:34")
    d.setTextSize(2)
    d.setTextColor(ORANGE_, BLACK_)
    d.drawString("10-10-2026", 40, 20)
    full, _ = timed(d.flush)
    result("t02_clock", "INFO", "clock screen flushed in full: %.1f ms" % full)
    times = []
    for m in ("35", "36", "37", "38", "39"):
        def tick():
            digit(d, 186, 70, m[1])
            return d.flush()
        ms, sent = timed(tick)
        times.append((ms, sent))
        time.sleep_ms(400)
    avg = sum(t[0] for t in times) / len(times)
    result("t02_clock", "PASS" if avg < 20 else "INFO", "one minute digit changed: %.1f ms on average, %d bytes sent (vs 115200 for the whole screen)" % (avg, times[0][1]))


TEXT = ("Kupic orzechy dla", "wiewiorki i sprawdzic", "czy karmnik jest", "pelny. Zadzwonic do", "Tomka w sprawie", "wyjazdu w sobote.",
        "Oddac ksiazke do", "biblioteki do konca", "tygodnia. Pomodoro:", "4 bloki po 25 min.", "Nie zapomniec o", "przerwach! :)", "-- koniec --")


def t03_text():
    d = disp()

    def draw():
        d.fillScreen(BLACK_)
        d.setTextSize(2)
        d.setTextColor(0xFFFFFF, BLACK_)
        for i, line in enumerate(TEXT):
            d.drawString(line[:15], 0, 6 + i * 18)
        return d.flush()
    ms, sent = timed(draw)
    result("t03_text", "PASS" if ms < 150 else "INFO", "13 lines of text (size 2): drawn and flushed in %.1f ms" % ms)
    time.sleep_ms(1500)


def t05_fast():
    """The same scenes with: CPU 240 MHz, glyphs cached in colour (blit without palette), a changed rectangle sent
    in one SPI write."""
    import machine
    machine.freq(240000000)
    d = disp()
    d.fast = True
    result("t05_fast", "INFO", "CPU %d MHz, colour glyphs, gathered flush" % (machine.freq() // 1000000))
    draw_menu(d, 0)                                    # build the glyph cache for the menu
    d.flush()
    full, _ = timed(lambda: (draw_menu(d, 1), d.flush()))
    result("t05_fast", "INFO", "full menu redraw + flush: %.1f ms" % full)
    d.fillScreen(BLACK_)
    draw_clock(d, "12:34")
    d.flush()
    ts = []
    for m in "56789":
        ms, _ = timed(lambda: (digit(d, 186, 70, m), d.flush()))
        ts.append(ms)
        time.sleep_ms(300)
    result("t05_fast", "INFO", "one minute digit changed: %.1f ms on average" % (sum(ts) / len(ts)))
    t03_text()                                         # first pass builds the colour glyphs ...
    ms, _ = timed(lambda: (d.fillScreen(BLACK_), [d.drawString(l[:15], 0, 6 + i * 18) for i, l in enumerate(TEXT)], d.flush()))
    result("t05_fast", "PASS" if ms < 150 else "INFO", "13 lines of text, glyphs cached: %.1f ms" % ms)
    machine.freq(160000000)


import micropython


@micropython.viper
def _vglyph(buf: ptr16, bw: int, x: int, y: int, mask: ptr8, n: int, stride: int, fg: int, bg: int):
    """Write an n x n 1-bit glyph (rows of `stride` bytes) into the RGB565 buffer at x, y: native code."""
    row = 0
    while row < n:
        p = (y + row) * bw + x
        m = row * stride
        col = 0
        while col < n:
            if (mask[m + (col >> 3)] >> (7 - (col & 7))) & 1:
                buf[p + col] = fg
            else:
                buf[p + col] = bg
            col += 1
        row += 1


@micropython.viper
def _vgather(dst: ptr8, src: ptr8, bw2: int, x2: int, w2: int, y0: int, rows: int):
    """Copy `rows` rows of w2 bytes, starting at row y0 / byte column x2 of the screen buffer, into dst: native code."""
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


class VDisplay(FbDisplay):
    """FbDisplay with text and the flush of a partial rectangle in viper."""

    def drawString(self, s, x, y):
        size = self._size
        n = 8 * size
        if self._bg is None or y < 0 or y + n > H:
            return FbDisplay.drawString(self, s, x, y)
        fg, bg, buf = self._fg, self._bg, self.buf
        stride = (n + 7) // 8
        cx = x
        for ch in s:
            if cx + n > W:
                break
            g = self._masks.get((ch, size))
            if g is None:
                g = self._mask(ch, size)
            _vglyph(buf, W, cx, y, g, n, stride, fg, bg)
            cx += n
        self._mark(x, y, cx - x, n)

    def _mask(self, ch, size):
        fbm = self._glyph(ch, size)                       # the scaled 1-bit glyph (MONO_HLSB: rows of whole bytes)
        n = 8 * size
        stride = (n + 7) // 8
        raw = bytearray(stride * n)
        for yy in range(n):                              # copy its bytes out (MONO_HLSB is exactly this layout)
            for xb in range(stride):
                b = 0
                for bit in range(8):
                    xx = xb * 8 + bit
                    if xx < n and fbm.pixel(xx, yy):
                        b |= 0x80 >> bit
                raw[yy * stride + xb] = b
        self._masks[(ch, size)] = raw
        return raw

    def flush(self):
        d = self.dirty
        if d is None:
            return 0
        x0, y0, x1, y1 = d
        w = x1 - x0 + 1
        if w == W:
            return FbDisplay.flush(self)
        self.dirty = None
        h = y1 - y0 + 1
        scr = self.scr
        scr._window(x0, y0, w, h)
        rows = len(self._row) // (w * 2)
        y = y0
        while y <= y1:
            k = min(rows, y1 - y + 1)
            _vgather(self._row, self.buf, W * 2, x0 * 2, w * 2, y, k)
            scr.spi.write(memoryview(self._row)[:k * w * 2])
            y += k
        scr.cs(1)
        return w * h * 2


def t06_viper():
    """Text and partial flushes in viper (native code, no C module)."""
    import machine
    global _disp
    for mhz in (160, 240):
        machine.freq(mhz * 1000000)
        old = _disp
        d = VDisplay(screen())
        d._masks = {}
        _disp = d
        draw_menu(d, 0)
        d.flush()                                        # masks built
        menu, _ = timed(lambda: (draw_menu(d, 1), d.flush()))
        d.fillScreen(BLACK_)
        draw_clock(d, "12:34")
        d.flush()
        ts = []
        for m in "56789":
            ms, _ = timed(lambda: (digit(d, 186, 70, m), d.flush()))
            ts.append(ms)
            time.sleep_ms(200)

        def text():
            d.fillScreen(BLACK_)
            d.setTextSize(2)
            d.setTextColor(0xFFFFFF, BLACK_)
            for i, line in enumerate(TEXT):
                d.drawString(line[:15], 0, 6 + i * 18)
            return d.flush()
        text()                                           # masks built
        tx, _ = timed(text)
        d.setTextColor(GREEN_, BLACK_)
        ln, _ = timed(lambda: (d.drawString("Edytowany wiersz", 0, 6 + 4 * 18), d.flush()))
        result("t06_viper", "PASS" if tx < 100 else "INFO",
               "%d MHz: menu %.1f ms | clock digit %.1f ms | 13 lines of text %.1f ms | one edited line %.1f ms" % (
                   mhz, menu, sum(ts) / len(ts), tx, ln))
        time.sleep_ms(800)
    machine.freq(160000000)


def run(names):
    for name in names or DEFAULT:
        print("\n== " + name)
        try:
            globals()[name]()
        except Exception as e:
            result(name, "FAIL", "%s: %s" % (type(e).__name__, e))
    print("\n== done")
