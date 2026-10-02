"""vlw.py - write and read Processing / TFT_eSPI / LovyanGFX "smooth font" (.vlw) files.

The format (all numbers big-endian 32-bit):
  header   6 x int32   glyph count, version (11), font size, 0, ascent, descent
  glyphs   7 x int32   for each glyph: unicode, height, width, xAdvance, dY, dX, 0
                       (dY = rows from the baseline up to the top row, dX = left bearing)
  bitmaps  8-bit coverage (alpha), width*height bytes per glyph, in the same order
Glyphs are sorted by unicode, as the loaders expect.  The files are read by M5.Lcd.setFont(path) in UIFlow 2.
This module needs Pillow (and, optionally, fontTools) only to MAKE a font; reading needs nothing.
"""
import struct

DEFAULT_RANGES = (
    (0x20, 0x7E),      # ASCII
    (0xA0, 0xFF),      # Latin-1 supplement: German, French, Spanish, Italian, Portuguese ...
    (0x100, 0x17F),    # Latin Extended-A: Polish, Czech, Slovak, Hungarian, Turkish, Croatian, Baltic ...
    (0x2013, 0x2014), (0x2018, 0x201E), (0x2022, 0x2022), (0x2026, 0x2026), (0x20AC, 0x20AC),
    (0x2190, 0x2193),  # arrows
)


def codepoints(ranges=DEFAULT_RANGES):
    out = []
    for lo, hi in ranges:
        out.extend(cp for cp in range(lo, hi + 1) if cp != 0xAD)      # U+00AD (soft hyphen) has no width
    return out


def _supported(ttf_path, wanted):
    try:
        from fontTools.ttLib import TTFont
        cmap = TTFont(ttf_path).getBestCmap()
        return [cp for cp in wanted if cp in cmap]
    except Exception:
        return list(wanted)


def make_glyphs(ttf_path, size, wanted, advance=None, threshold=None):
    """Render glyphs with Pillow.  advance: force this x-advance (monospace); threshold: 1-bit look (0-255)."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(ttf_path, size)
    pad, base = size, size * 2
    glyphs = []
    for cp in _supported(ttf_path, wanted):
        ch = chr(cp)
        img = Image.new("L", (size * 3, size * 3), 0)
        ImageDraw.Draw(img).text((pad, base), ch, font=font, fill=255, anchor="ls")
        if threshold is not None:
            img = img.point(lambda v: 255 if v >= threshold else 0)
        adv = advance if advance is not None else int(round(font.getlength(ch)))
        box = img.getbbox()
        if box is None:
            glyphs.append(dict(unicode=cp, width=0, height=0, advance=adv, dY=0, dX=0, data=b""))
            continue
        left, top, right, bottom = box
        glyphs.append(dict(unicode=cp, width=right - left, height=bottom - top, advance=adv,
                           dY=base - top, dX=left - pad, data=img.crop(box).tobytes()))
    glyphs.sort(key=lambda g: g["unicode"])
    return glyphs


def build(glyphs, size):
    ascent = max([g["dY"] for g in glyphs if g["height"]] + [0])
    descent = max([g["height"] - g["dY"] for g in glyphs if g["height"]] + [0])
    out = bytearray(struct.pack(">6i", len(glyphs), 11, size, 0, ascent, descent))
    for g in glyphs:
        out += struct.pack(">7i", g["unicode"], g["height"], g["width"], g["advance"], g["dY"], g["dX"], 0)
    for g in glyphs:
        out += g["data"]
    return bytes(out)


def parse(data):
    """Read a .vlw back.  Returns (header dict, {unicode: glyph dict with 'data'}).  Raises ValueError if it is damaged."""
    if len(data) < 24:
        raise ValueError("too short for a header")
    count, version, size, _zero, ascent, descent = struct.unpack(">6i", data[:24])
    if version != 11 or not 0 < count < 5000:
        raise ValueError("unexpected header: count=%d version=%d" % (count, version))
    pos = 24
    heads = []
    for _ in range(count):
        if pos + 28 > len(data):
            raise ValueError("glyph table cut short")
        uni, h, w, adv, dy, dx, _pad = struct.unpack(">7i", data[pos:pos + 28])
        heads.append((uni, h, w, adv, dy, dx))
        pos += 28
    glyphs = {}
    for uni, h, w, adv, dy, dx in heads:
        n = h * w
        if pos + n > len(data):
            raise ValueError("bitmap data cut short at U+%04X" % uni)
        glyphs[uni] = dict(unicode=uni, height=h, width=w, advance=adv, dY=dy, dX=dx, data=data[pos:pos + n])
        pos += n
    return dict(count=count, size=size, ascent=ascent, descent=descent, order=[h[0] for h in heads], end=pos, length=len(data)), glyphs


def render_text(text, glyphs, header, scale=1):
    """Draw `text` the way a loader would (baseline = ascent), into a Pillow 'L' image - for previews and tests."""
    from PIL import Image
    ascent, descent = header["ascent"], header["descent"]
    width = sum(glyphs[ord(c)]["advance"] for c in text if ord(c) in glyphs) + 2
    img = Image.new("L", (width, ascent + descent + 1), 0)
    x = 0
    for ch in text:
        g = glyphs.get(ord(ch))
        if not g:
            continue
        if g["width"]:
            tile = Image.frombytes("L", (g["width"], g["height"]), g["data"])
            img.paste(tile, (x + g["dX"], ascent - g["dY"]))
        x += g["advance"]
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST) if scale != 1 else img
