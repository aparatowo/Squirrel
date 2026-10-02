#!/usr/bin/env python3
"""check_vlw.py - look inside a .vlw file: header, glyph coverage, and a text preview in the terminal.

    python3 tools/check_vlw.py squirrel.vlw "Zażółć gęślą jaźń"
    python3 tools/check_vlw.py squirrel.vlw "Zażółć" --png preview.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlw

POLISH = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("font")
    ap.add_argument("text", nargs="?", default="Zażółć gęślą jaźń 0123")
    ap.add_argument("--png", help="also write the preview as a PNG (5x)")
    args = ap.parse_args()
    data = open(args.font, "rb").read()
    header, glyphs = vlw.parse(data)
    print("%s: %d glyphs, %d bytes; ascent %d, descent %d, size %d"
          % (args.font, header["count"], len(data), header["ascent"], header["descent"], header["size"]))
    print("sorted by unicode:", header["order"] == sorted(header["order"]), "| file length matches:", header["end"] == header["length"])
    print("advances:", sorted({g["advance"] for g in glyphs.values() if g["unicode"] > 0x20}))
    print("Polish letters present:", "".join(c for c in POLISH if ord(c) in glyphs), "| missing:", "".join(c for c in POLISH if ord(c) not in glyphs) or "none")
    img = vlw.render_text(args.text, glyphs, header)
    for y in range(img.height):
        print("".join("#" if img.getpixel((x, y)) > 100 else ("+" if img.getpixel((x, y)) > 30 else ".") for x in range(img.width)))
    if args.png:
        img.resize((img.width * 5, img.height * 5)).save(args.png)
        print("wrote", args.png)


if __name__ == "__main__":
    main()
