# tools/sim/check_trace.py - what looks wrong in a simulator trace (tools/sim/crawl_scenario.py), picture by picture
#
#   python3 tools/sim/check_trace.py <trace> [--lang pl] [--height 135]
# Reports, with the name of the next picture (SHOT) so it can be looked at:
#   OFF     text that runs past the right or bottom edge (drawn with the 6 x 8 font: the Cardputer's .vlw font is a
#           little different - a text right at the edge is worth a look on the device)
#   ENGLISH a text drawn in English although the language's table has another text for it (--lang); also an
#           English phrase of two words or more inside a longer text (a label after "# ")
#   ERROR   lines of the log that say something failed (pass the console output with --log)
import argparse
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "i18n"))


def catalogue(lang):
    import build
    _langs, rows = build.read_catalog()
    return {en: tr[lang] for en, tr in rows.items() if tr.get(lang) and tr[lang] != en}


def check(trace, lang=None, height=135, width=240):
    english = catalogue(lang) if lang and lang != "en" else {}
    # phrases worth finding inside other texts: two words or more, no placeholders, not a word of the language itself
    phrases = [en for en in english if " " in en.strip() and "%" not in en and len(en.strip()) >= 8]
    size, pending, out = 1, [], []
    for line in open(trace, encoding="utf-8").read().splitlines():
        if line.startswith("SHOT "):
            name = line[5:].strip()
            out += ["%-8s %s: %s" % (kind, name, text) for kind, text in pending]
            pending = []
            continue
        m = re.match(r"(\w+)\((.*)\)$", line)
        if not m:
            continue
        call, args = m.group(1), m.group(2)
        if call == "fillScreen":
            pending = []                               # a new picture: what was drawn before is gone
            continue
        try:
            a = ast.literal_eval("(" + args + ",)") if args else ()
        except (ValueError, SyntaxError):
            continue
        if call == "setTextSize":
            size = int(a[0])
        elif call == "drawString" and len(a) >= 3:
            text, x, y = str(a[0]), int(a[1]), int(a[2])
            right, bottom = x + 6 * size * len(text), y + 8 * size
            if text.strip() and (right > width + 1 or bottom > height + 1 or x < 0 or y < 0):
                pending.append(("OFF", "%r at %d,%d size %d (to x %d, y %d)" % (text, x, y, size, right, bottom)))
            stripped = text.strip()
            if stripped in english and len(stripped) > 2 and not stripped.isdigit():
                pending.append(("ENGLISH", "%r (table: %r)" % (stripped, english[stripped])))
            else:
                for en in phrases:                      # an English phrase inside a longer text ("# " + a label)
                    if en in text and english[en] not in text:
                        pending.append(("ENGLISH", "%r in %r (table: %r)" % (en, text, english[en])))
                        break
    seen, unique = set(), []
    for line in out:
        key = line.split(": ", 1)[1] if ": " in line else line
        if key not in seen:
            seen.add(key)
            unique.append(line)
    return unique


def log_errors(path):
    words = ("Traceback", "[ERROR]", "[SERVICE]", "HOME forced", "Error:", "failed")
    return ["ERROR    %s" % l for l in open(path, encoding="utf-8", errors="replace").read().splitlines()
            if any(w in l for w in words)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="What looks wrong in a simulator trace.")
    ap.add_argument("trace")
    ap.add_argument("--lang")
    ap.add_argument("--height", type=int, default=135)
    ap.add_argument("--log", help="the simulator's console output, for its errors")
    a = ap.parse_args()
    found = check(a.trace, a.lang, a.height) + (log_errors(a.log) if a.log else [])
    print("\n".join(found) if found else "nothing found")
    print("%d findings (each text once)" % len(found))
