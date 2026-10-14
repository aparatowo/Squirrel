# i18n.py - the user interface in English, Polish, French or German (the setting LANGUAGE)
#
#   from i18n import _
#   Lcd.drawString(_("Saved"), 5, 5)
#   _("Synced %d of %d") % (done, total)          # translate the pattern, then fill it in
#
# The texts are English in the code.  lang/<code>.py holds T = (english, translated, english, translated, ...) sorted
# by the English text: _() finds a text by binary search.  Frozen into the firmware that tuple stays in flash - a
# language costs next to no RAM.  A text with no translation is shown in English.  Letters the display cannot draw
# (no font loaded) are folded to ASCII by gfx.drawString, as for any other text.
# The tables are generated from translations/<code>.tsv by tools/i18n/build.py; tools/i18n/check.py lists the texts
# of the code that have no translation yet.
# Your own texts, no new firmware needed: <BASE_DIR>/lang_<code>.tsv on the device (the SD card's /Squirrel on the
# Cardputer), in the format of translations/<code>.tsv - only the lines you want different.  They win over the table
# (lang_en.tsv changes the English texts too) and are the only texts kept in RAM.  Data (menus, settings, their help) stays English in its own files and is
# translated where it is drawn.
LANGUAGES = ("en", "pl", "fr", "de")

_code = "en"
_table = None
_cache = {}                  # text -> translation, of the texts drawn lately (a screen draws the same ones again)
_CACHE_MAX = 200             # then it starts over: a few KB at most
_attached = False            # listening to the setting (appconfig's on_change): _() itself reads nothing
_own = None                  # the user's own texts for this language (lang_<code>.tsv), or None


def _wanted():
    try:
        from appconfig import cfg
        code = cfg.get("LANGUAGE")
    except Exception:
        return "en"
    return code if code in LANGUAGES else "en"


def _on_change(key, value):
    if key == "LANGUAGE":
        _load(value if value in LANGUAGES else "en")


def _attach():
    global _attached
    _attached = True
    try:
        from appconfig import cfg
        cfg.on_change(_on_change)
    except Exception:
        pass
    _load(_wanted())


def _read_own(code):
    """{english: text} of the user's file lang_<code>.tsv, or None (no file, or nothing in it)."""
    try:
        import nuts
        f = open("%s/lang_%s.tsv" % (nuts.BASE_DIR, code), encoding="utf-8")
    except (ImportError, OSError, AttributeError):
        return None
    out = {}
    with f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line or line.startswith("en\t") or "\t" not in line:
                continue
            en, _sep, text = line.partition("\t")
            if text:
                out[en.replace("\\n", "\n")] = text.replace("\\n", "\n")
    print("[I18N] %d texts of your own (lang_%s.tsv)" % (len(out), code))
    return out or None


def _load(code):
    global _code, _table, _own
    _code, _table = code, None
    _cache.clear()
    _own = _read_own(code)
    if code == "en":
        return
    try:
        _table = __import__("lang." + code, None, None, ("T",)).T
    except (ImportError, AttributeError) as e:
        print("[I18N] no table for %s: %s" % (code, e))


def language():
    if not _attached:
        _attach()
    return _code


def _(text):
    """`text` in the current language (English when there is no translation).  Every call is cheap - a function
    call costs ~50 us on the watch at 80 MHz, and a screen draws dozens of texts: the setting is not read here."""
    if not _attached:
        _attach()
    if _own is not None:
        hit = _own.get(text)
        if hit is not None:
            return hit
    if _table is None:
        return text
    hit = _cache.get(text)
    if hit is not None:
        return hit
    if len(_cache) >= _CACHE_MAX:
        _cache.clear()
    hit = _cache[text] = _find(text)
    return hit


def _find(text):
    t = _table
    lo, hi = 0, len(t) // 2
    while lo < hi:
        mid = (lo + hi) // 2
        key = t[2 * mid]
        if key < text:
            lo = mid + 1
        elif key > text:
            hi = mid
        else:
            return t[2 * mid + 1]
    return text


def _pieces(template):
    """'Synced %d of %d' -> ['Synced ', ' of ', ''] (the text between the placeholders; %% is a plain %)."""
    out, cur, i, n = [], "", 0, len(template)
    while i < n:
        ch = template[i]
        if ch == "%" and i + 1 < n and template[i + 1] == "%":
            cur += "%"
            i += 2
            continue
        if ch == "%":
            j = i + 1
            while j < n and template[j] in "-+#0123456789.":
                j += 1
            out.append(cur)
            cur = ""
            i = j + 1
            continue
        cur += ch
        i += 1
    out.append(cur)
    return out


def _values(text, pieces):
    """The values a template with these pieces was filled with, or None when `text` is not made from it."""
    if not text.startswith(pieces[0]):
        return None
    pos, values = len(pieces[0]), []
    for k in range(1, len(pieces)):
        piece = pieces[k]
        if k == len(pieces) - 1:
            if not text.endswith(piece) or len(text) - len(piece) < pos:
                return None
            end = len(text) - len(piece)
        else:
            end = text.find(piece, pos) if piece else -1
            if end < 0:
                return None
        values.append(text[pos:end])
        pos = end + len(piece)
    return values


def fill(text, templates, inner=None):
    """A text made by filling in one of `templates` (English, e.g. "Synced %d of %d") -> the same text in the current
    language, with the same values: for modules that keep their messages in English (their logic reads them).
    inner: templates for the values themselves ("failed: %s" with %s = "wrong code"), translated the same way."""
    if language() == "en":
        return text
    for template in templates:
        pieces = _pieces(template)
        if len(pieces) < 2:
            if text == template:
                return _(text)
            continue
        values = _values(text, pieces)
        if values is not None:
            out = _pieces(_(template))
            if len(out) != len(pieces):
                return text                     # a translation with other placeholders: English rather than wrong
            if inner:
                values = [fill(v, inner) for v in values]
            return "".join(out[k] + (values[k] if k < len(values) else "") for k in range(len(out)))
    return _(text)
