# tools/i18n/unwrapped.py - string literals that look like user-interface text but have no _() around them
#
#   python3 tools/i18n/unwrapped.py screens/*.py ...
# A heuristic for marking files: a literal with a word in it that is not a subscript, a docstring, a log line or
# wrapped already.  Not every hit is UI text (keys, file names): the list is for reading, not for fixing blindly.
import io
import re
import sys
import tokenize

WORD = re.compile(r"[A-Za-z]{3}")
SKIP_LINE = re.compile(r"\blog\(|print\(|trace\(|raise |getattr\(|setattr\(|hasattr\(|__import__|import |"
                       r"set_screen\(|cfg\.(get|set)|\.startswith|\.endswith|open\(|\.get\(\"|menu_name=")


def scan(path):
    src = open(path, encoding="utf-8").read()
    lines = src.splitlines()
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    out = []
    for i, tok in enumerate(toks):
        if tok.type != tokenize.STRING:
            continue
        text = tok.string
        prefix = re.match(r"[A-Za-z]*", text).group(0).lower()
        if "b" in prefix or text.startswith(('"""', "'''")) or not WORD.search(text):
            continue
        body = text[len(prefix) + 1:-1]
        if re.fullmatch(r"[A-Z0-9_]+", body) or re.fullmatch(r"[a-z0-9_.:/]+", body):
            continue                              # a key, a code, a file name
        prev = [t for t in toks[max(0, i - 3):i] if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT)]
        if prev and prev[-1].string == "[":
            continue
        if len(prev) >= 2 and prev[-1].string == "(" and prev[-2].string == "_":
            continue
        line = lines[tok.start[0] - 1]
        if SKIP_LINE.search(line):
            continue
        out.append("%s:%d  %s" % (path, tok.start[0], text[:90]))
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        for hit in scan(p):
            print(hit)
