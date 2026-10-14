# tools/i18n/check.py - is every text of the user interface translated, and are the translations sound?
#
#   python3 tools/i18n/check.py             a summary; exit 1 when something is missing or wrong
#   python3 tools/i18n/check.py --missing   also list the missing texts, with where they are used
#   python3 tools/i18n/check.py --add       add the missing texts to every translations/<code>.tsv, to be translated
# Checks: a text of the code / the data with no line in the catalogue, a catalogue line nothing uses any more, a
# translation whose %-placeholders differ from the English (i18n.fill and the % formatting need the same ones, in
# the same order), a setting label longer than 18 characters (Personalize shows a label and a value on one row).
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build
import texts

PLACEHOLDER = re.compile(r"%[-+#0-9.]*[sdif%]")


def main(argv):
    used = texts.all_texts()
    langs, rows = build.read_catalog()
    problems = 0
    missing = [t for t in sorted(used) if t not in rows]
    unused = [t for t in sorted(rows) if t not in used]
    print("%d texts in the user interface, %d in the catalogue" % (len(used), len(rows)))
    if missing:
        problems += 1
        print("%d texts not in the catalogue%s" % (len(missing), "" if "--missing" in argv else " (--missing lists them)"))
        if "--missing" in argv:
            for t in missing:
                print("   %r   <- %s" % (t, ", ".join(used[t][:2])))
    if unused:
        print("%d catalogue lines nothing uses:" % len(unused))
        for t in unused:
            print("   %r" % t)
    from appconfig_schema import SETTINGS
    labels = {s[3] for s in SETTINGS}
    for en, tr in sorted(rows.items()):
        for code in langs:
            text = tr.get(code, "")
            if not text:
                continue
            if PLACEHOLDER.findall(text) != PLACEHOLDER.findall(en):
                problems += 1
                print("%s: placeholders differ: %r -> %r" % (code, en, text))
            if en in labels and len(text) > 18:
                problems += 1
                print("%s: label longer than 18: %r -> %r" % (code, en, text))
    for code in langs:
        done = sum(1 for t in used if rows.get(t, {}).get(code))
        print("  %s: %d of %d translated" % (code, done, len(used)))
        if done < len(used):
            problems += 1
    if "--add" in argv and missing:
        for t in missing:
            rows[t] = {code: "" for code in langs}
        build.write_catalog(langs, rows)
        print("added %d texts (untranslated) to translations/*.tsv" % len(missing))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
