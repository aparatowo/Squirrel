# charmap.py - characters beyond ASCII
#
# Two jobs, kept together because they describe the same alphabets:
#   * folding: turn "zażółć" into "zazolc".  fold() keeps the length (one character for one), so
#     that columns and cursors still line up - it is what the display falls back to when no font with
#     those letters is loaded.  ascii_name() is for file names and may expand (ß -> ss).
#   * typing: the keyboard has no Polish (or German ...) letters.  With a layout selected, ALT + a letter
#     types the accented one, as AltGr does on the Polish programmer's keyboard: ALT+a = ą, ALT+s = ś ...
#     (with Aa active: Ą, Ś ...).  compose() turns the action "ALT+a" into "ą".

_SRC = '¨ª¯²³´¸¹º¼½¾ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽžſ'
_DST = ' a 23  1o113AAAAAAACEEEEIIIIDNOOOOOOUUUUYPsaaaaaaaceeeeiiiidnoooooouuuuypyAaAaAaCcCcCcCcDdDdEeEeEeEeEeGgGgGgGgHhHhIiIiIiIiIiIiJjKkkLlLlLlLlLlNnNnNnnNnOoOoOoOoRrRrRrSsSsSsSsTtTtTtUuUuUuUuUuUuWwYyYZzZzZzs'
_MULTI = {"ß": "ss", "Æ": "AE", "æ": "ae", "Œ": "OE", "œ": "oe", "Þ": "Th", "þ": "th", "Ĳ": "IJ", "ĳ": "ij"}

# layout name -> {plain letter: letter typed with ALT}.  "en" has none.
LAYOUTS = {
    "en": {},
    "pl": {"a": "ą", "c": "ć", "e": "ę", "l": "ł", "n": "ń", "o": "ó", "s": "ś", "x": "ź", "z": "ż",
           "A": "Ą", "C": "Ć", "E": "Ę", "L": "Ł", "N": "Ń", "O": "Ó", "S": "Ś", "X": "Ź", "Z": "Ż"},
    "de": {"a": "ä", "o": "ö", "u": "ü", "s": "ß", "A": "Ä", "O": "Ö", "U": "Ü"},
}
LAYOUT_NAMES = ("pl", "en", "de")


def is_ascii(text):
    try:
        return len(text.encode()) == len(text)
    except Exception:
        return False


def fold(text):
    """Same length, ASCII only: ą -> a, ł -> l, ß -> s ... (anything unknown becomes '?')."""
    if is_ascii(text):
        return text
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
        else:
            i = _SRC.find(ch)
            out.append(_DST[i] if i >= 0 else "?")
    return "".join(out)


def ascii_name(text):
    """For file names: like fold(), but ß -> ss, æ -> ae ... (the length may change)."""
    if is_ascii(text):
        return text
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
        elif ch in _MULTI:
            out.append(_MULTI[ch])
        else:
            i = _SRC.find(ch)
            out.append(_DST[i] if i >= 0 else "_")
    return "".join(out)


def compose(action, layout):
    """'ALT+a' -> 'ą' with the Polish layout; anything else is returned unchanged."""
    if len(action) == 5 and action.startswith("ALT+"):
        return LAYOUTS.get(layout, {}).get(action[4], action)
    return action
