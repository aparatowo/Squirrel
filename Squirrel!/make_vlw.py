#!/usr/bin/env python3
"""make_vlw.py - make the Squirrel! font (a .vlw file) from a TrueType font.

    python3 tools/make_vlw.py                       # DejaVu Sans Mono, 10 px, 6 px per character, sharp
    python3 tools/make_vlw.py --antialias           # smooth edges instead of sharp ones
    python3 tools/make_vlw.py --ttf /path/to/Other.ttf --size 10 --advance 6 --out squirrel.vlw

Needs Pillow (pip install pillow); fontTools (pip install fonttools) is used if present to skip letters
the font does not have.  The result goes to /flash/apps/Squirrel/fonts/squirrel.vlw on the device.

Keep --advance at 6 and the font monospaced: the screens are laid out in 6-pixel columns.
A font with a different advance can be used, but then the columns (36 per line) change.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlw

DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ttf", default=DEJAVU, help="TrueType font (monospaced). Default: DejaVu Sans Mono")
    ap.add_argument("--size", type=int, default=10, help="pixel size (default 10: 6 px per character for DejaVu Sans Mono)")
    ap.add_argument("--advance", type=int, default=6, help="pixels per character (default 6)")
    ap.add_argument("--antialias", action="store_true", help="smooth edges (default: sharp, like the built-in font)")
    ap.add_argument("--threshold", type=int, default=110, help="sharpness cut-off 1-255 (default 110)")
    ap.add_argument("--out", default="squirrel.vlw")
    args = ap.parse_args()
    glyphs = vlw.make_glyphs(args.ttf, args.size, vlw.codepoints(), advance=args.advance,
                             threshold=None if args.antialias else args.threshold)
    data = vlw.build(glyphs, args.size)
    header, _parsed = vlw.parse(data)                      # read it back: a damaged file is caught here
    with open(args.out, "wb") as f:
        f.write(data)
    print("%s: %d glyphs, %d bytes, line height %d px (ascent %d, descent %d), %d px per character"
          % (args.out, header["count"], len(data), header["ascent"] + header["descent"], header["ascent"], header["descent"], args.advance))


if __name__ == "__main__":
    main()
