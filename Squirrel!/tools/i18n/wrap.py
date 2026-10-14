# tools/i18n/wrap.py - put _() around the texts a screen draws (a helper for marking a file; review the diff after it)
#
#   python3 tools/i18n/wrap.py screens/foo.py ...        (from the folder with squirrel_app.py)
# On the lines that draw or show text (drawString, render_options, render_menu, draw_header, status = ..., _result
# = ...) every plain string literal with a word in it is wrapped - "A" if x else "B" and "...%d..." % v included -
# unless it is a subscript (theme["FG"]), an f-string (those are rewritten by hand) or wrapped already.  Adds
# "from i18n import _" when the file had none.
import io
import re
import sys
import tokenize

TARGETS = re.compile(r"drawString\(|render_options\(|render_menu\(|draw_header\(|\.status = |_result = |_notify\(|"
                     r"render_notification\(|render_delete_confirm\(|label = ")
WORD = re.compile(r"[A-Za-z]{2}")


def wrap_file(path):
    src = open(path, encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    edits = []                                    # (row, col_start, col_end)
    for i, tok in enumerate(toks):
        if tok.type != tokenize.STRING or tok.start[0] != tok.end[0]:
            continue
        line = lines[tok.start[0] - 1]
        if not TARGETS.search(line):
            continue
        text = tok.string
        prefix = re.match(r"[A-Za-z]*", text).group(0).lower()
        if "f" in prefix or "b" in prefix or not WORD.search(text):
            continue
        prev = [t for t in toks[max(0, i - 3):i] if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT)]
        if prev and prev[-1].string == "[":
            continue                              # a key: theme["FG"]
        if len(prev) >= 2 and prev[-1].string == "(" and prev[-2].string == "_":
            continue                              # wrapped already
        edits.append((tok.start[0], tok.start[1], tok.end[1]))
    for row, a, b in sorted(edits, reverse=True):
        line = lines[row - 1]
        lines[row - 1] = line[:a] + "_(" + line[a:b] + ")" + line[b:]
    out = "".join(lines)
    if edits and not re.search(r"^from i18n import _", out, re.M):
        m = list(re.finditer(r"^(import [^\n]+|from [^\n]+ import [^\n]+)\n", out, re.M))
        at = m[-1].end() if m else 0
        out = out[:at] + "from i18n import _\n" + out[at:]
    if out != src:
        open(path, "w", encoding="utf-8").write(out)
    return len(edits)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print("%-40s %d" % (p, wrap_file(p)))
