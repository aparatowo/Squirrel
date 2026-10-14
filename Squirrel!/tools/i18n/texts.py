# tools/i18n/texts.py - every English text of the user interface, as the translation catalogue needs them
#
# Two sources: the literals of the code inside _("...") (or tr("...") where _ is taken), and the data that is
# translated where it is drawn - menus, settings and their help, option values, the message templates of modules
# that keep English messages (i18n.fill), constants of screens.  Used by check.py and build.py.
import ast
import io
import os
import sys
import tokenize

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
SKIP_DIRS = {"tools", "vendor", ".build", "__pycache__", "dist", "lang", ".git", "archive", "firmware_patches", "translations"}

# (file, constant, which texts of it): "all" = every string in it, "values" = a dict's values, "labels" = item 1 of
# each tuple, "keys0" = item 0 of each tuple
DATA = (
    ("screens/clock_screen.py", "_WEEKDAYS", "all"),
    ("screens/clock_screen.py", "_FOCUS_MESSAGES", "values"),
    ("screens/clock_screen.py", "_QUICK", "labels"),
    ("screens/alarms_screen.py", "_WEEKDAYS", "all"),
    ("screens/focus_stats_screen.py", "_DAY_NAMES", "all"),
    ("appconfig.py", "_DAY_SHORT", "all"),
    ("screens/rhythm_screens.py", "EXERCISES", "keys0"),
    ("screens/rhythm_screens.py", "PHASES", "all"),
    ("screens/silent_mode_screen.py", "_TITLES", "values"),
    ("screens/personalize_screen.py", "_RESET_ALL", "all"),
    ("screens/wifi_screen.py", "_ADD", "all"),
    ("screens/set_time_screen.py", "_FIELDS", "keys0"),
    ("intervals.py", "NAMES", "values"),
    ("ble/central.py", "STATUS_TEMPLATES", "all"),
    ("ble/central.py", "RESULT_TEMPLATES", "all"),
    ("ble/central.py", "REASON_TEMPLATES", "all"),
    ("time_sync.py", "MESSAGE_TEMPLATES", "all"),
)
# texts made by the code that no single literal shows
EXTRA = ("deep", "FINISHED", "RUNNING", "PAUSED", "Pomodoro", "Training", "Done", "Cancel", "Skip", "OK", "Close",
         "Silent: sound", "Silent: buzzer", "Silent: LED")


def _constant(path, name):
    tree = ast.parse(open(os.path.join(APP, path), encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError("%s: no %s" % (path, name))


def _strings(value, how):
    if how == "values":
        return [v for v in value.values() if isinstance(v, str)]
    if how == "labels":
        return [item[1] for item in value]
    if how == "keys0":
        return [item[0] for item in value]
    if isinstance(value, str):
        return [value]
    return [v for v in value if isinstance(v, str)]


def code_texts():
    """{text: [file:line, ...]} of the literals inside _() / tr()."""
    found = {}
    for root, dirs, files in os.walk(APP):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            src = open(path, encoding="utf-8").read()
            try:
                toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
            except (tokenize.TokenError, IndentationError):
                continue
            for i in range(2, len(toks)):
                t = toks[i]
                if t.type != tokenize.STRING or toks[i - 1].string != "(" or toks[i - 2].string not in ("_", "tr"):
                    continue
                if i + 1 < len(toks) and toks[i + 1].string != ")":
                    continue                       # _("a" "b") or _(x + "y"): not a plain literal
                try:
                    text = ast.literal_eval(t.string)
                except (ValueError, SyntaxError):
                    continue
                if isinstance(text, str):
                    found.setdefault(text, []).append("%s:%d" % (os.path.relpath(path, APP), t.start[0]))
    return found


def data_texts():
    """{text: [where]} of the data translated where it is drawn."""
    sys.path.insert(0, APP)
    found = {}

    def add(text, where):
        if text and any(c.isalpha() for c in text):
            found.setdefault(text, []).append(where)

    import port_config                      # every port's menus: none hidden while the texts are gathered
    for name in ("HIDDEN_MENUS", "HIDDEN_SCREENS", "HIDDEN_ACTIONS", "HIDDEN_GROUPS"):
        setattr(port_config, name, frozenset())
    import menu_tree
    import appconfig_schema as schema
    import nuts
    for menu, (title, entries) in menu_tree.MENUS.items():
        add(title, "menu " + menu)
        for entry in entries:
            add(entry[0], "menu " + menu)
    for key, (title, _ext) in menu_tree.COLLECTIONS.items():
        add(title, "list " + key)
    for key, kind, group, label, extra in schema.SETTINGS:
        add(label, "setting " + key)
        add(group, "group")
        if kind == "choice":
            for option in extra:
                add(str(option), "option " + key)
    for key, text in schema.HELP.items():
        add(text, "help " + key)
    for name in getattr(nuts, "PALETTE", {}):
        add(name, "colour")
    for text in ("on", "off"):
        add(text, "bool")
    for path, name, how in DATA:
        for text in _strings(_constant(path, name), how):
            add(text, "%s %s" % (path, name))
    for text in EXTRA:
        add(text, "extra")
    return found


def all_texts():
    texts = code_texts()
    for text, where in data_texts().items():
        texts.setdefault(text, []).extend(where)
    return texts
