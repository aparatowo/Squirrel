# tools/sim/render_shots.py - the Cardputer's screens as PNG pictures, from a trace of the simulator (run_sim.py)
#
#   python3 tools/sim/render_shots.py <trace.txt> <out folder> [--scale 2] [--prefix en]
# The trace is every drawing call the app made, in order.  Here they are drawn again on a 240 x 135 canvas with the
# font the device uses by default (the classic 5 x 7 of Adafruit GFX, drivers/glcdfont.py - M5GFX's too - with the
# accented letters of drivers/glcdfont_latin.py standing in for the .vlw font of the other languages), and the
# canvas is saved just before every key press: what the user saw at that moment.  A picture equal to the one before
# is not saved again.  Names: <prefix>_<number>_<section of the scenario>.png.  A trace with SHOT markers
# (tools/sim/shots_scenario.py) gives only those pictures, named <shot>.png.
import argparse
import ast
import hashlib
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from drivers.glcdfont import FONT
from drivers.glcdfont_latin import CHARS as LATIN, DATA as LATIN_DATA

W, H = 240, 135


def rgb(c):
    return (c >> 16 & 255, c >> 8 & 255, c & 255)


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W, H))
        self.px = self.img.load()
        self.fg, self.bg, self.size = (255, 255, 255), None, 1

    def rect(self, x, y, w, h, c, fill=True):
        for yy in range(max(0, y), min(H, y + h)):
            for xx in range(max(0, x), min(W, x + w)):
                if fill or yy in (y, y + h - 1) or xx in (x, x + w - 1):
                    self.px[xx, yy] = c

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(max(0, cy - r), min(H, cy + r + 1)):
            for xx in range(max(0, cx - r), min(W, cx + r + 1)):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if d <= r * r and (fill or d >= (r - 1) * (r - 1)):
                    self.px[xx, yy] = c

    def text(self, s, x, y):
        n = self.size
        for ch in s:
            font, base = FONT, 5 * ord(ch)
            if ord(ch) > 127:                       # the accented letters of the watch's font (glcdfont_latin)
                i = LATIN.find(ch)
                font, base = (LATIN_DATA, 5 * i) if i >= 0 else (FONT, 5 * 0x3F)
            for col in range(6):
                bits = font[base + col] if col < 5 else 0
                for row in range(8):
                    on = bits >> row & 1
                    colour = self.fg if on else self.bg
                    if colour is None:
                        continue
                    for dy in range(n):
                        for dx in range(n):
                            xx, yy = x + col * n + dx, y + row * n + dy
                            if 0 <= xx < W and 0 <= yy < H:
                                self.px[xx, yy] = colour
            x += 6 * n


def render(trace, out, scale=2, prefix="shot"):
    os.makedirs(out, exist_ok=True)
    cv = Canvas()
    section, saved, last = "start", 0, None
    count = 0
    lines = open(trace, encoding="utf-8").read().splitlines()
    named = any(l.startswith("SHOT ") for l in lines)
    for line in lines:
        if line.startswith("SHOT "):
            img = cv.img.resize((W * scale, H * scale), Image.NEAREST) if scale > 1 else cv.img
            img.save(os.path.join(out, line[5:].strip() + ".png"))
            saved += 1
            continue
        if named and line.startswith("KEY "):
            continue
        if line.startswith("== "):
            section = re.sub(r"[^a-z0-9]+", "-", line.strip("= ").lower()).strip("-")
            continue
        if line.startswith("KEY "):
            data = cv.img.tobytes()
            digest = hashlib.md5(data).hexdigest()
            if digest != last:
                last = digest
                count += 1
                name = "%s_%04d_%s.png" % (prefix, count, section)
                img = cv.img.resize((W * scale, H * scale), Image.NEAREST) if scale > 1 else cv.img
                img.save(os.path.join(out, name))
                saved += 1
            continue
        m = re.match(r"(\w+)\((.*)\)$", line)
        if not m:
            continue
        name, args = m.group(1), m.group(2)
        try:
            a = ast.literal_eval("(" + args + ",)") if args else ()
        except (ValueError, SyntaxError):
            continue
        if name == "fillScreen":
            cv.rect(0, 0, W, H, rgb(a[0]))
        elif name == "fillRect":
            cv.rect(a[0], a[1], a[2], a[3], rgb(a[4]))
        elif name == "drawRect":
            cv.rect(a[0], a[1], a[2], a[3], rgb(a[4]), fill=False)
        elif name == "fillCircle":
            cv.circle(a[0], a[1], a[2], rgb(a[3]))
        elif name == "drawCircle":
            cv.circle(a[0], a[1], a[2], rgb(a[3]), fill=False)
        elif name == "drawPixel":
            if 0 <= a[0] < W and 0 <= a[1] < H:
                cv.px[a[0], a[1]] = rgb(a[2])
        elif name == "setTextColor":
            cv.fg = rgb(a[0])
            cv.bg = rgb(a[1]) if len(a) > 1 else None
        elif name == "setTextSize":
            cv.size = int(a[0])
        elif name == "drawString":
            cv.text(str(a[0]), int(a[1]), int(a[2]))
    return saved


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The Cardputer's screens from a simulator trace, as PNG pictures.")
    ap.add_argument("trace")
    ap.add_argument("out")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--prefix", default="shot")
    a = ap.parse_args()
    print("%d pictures in %s" % (render(a.trace, a.out, a.scale, a.prefix), a.out))
