# tools/sim/crawl_scenario.py - every screen, as deep as it goes: for checking the whole app after a change
#
#   SQUIRREL_SIM_SCENARIO=tools/sim/crawl_scenario.py micropython -X heapsize=8M tools/sim/run_sim.py <app> <work> <trace>
#   python3 tools/sim/check_trace.py <trace> --lang pl            # what looks wrong: text off the screen, untranslated
#   python3 tools/sim/render_shots.py <trace> <folder>            # the pictures, to look at
# With SQUIRREL_SIM_TOUCH=1 the same app is shown as on a touch screen of 240 x 240 (the watch's layouts: TouchList,
# buttons, full-height screens) and driven by taps on the widgets (render with --height 240).  The features stay the
# Cardputer's, so the watch's screens are seen with more in them than the watch has - the layouts are what is checked.
#
# Runs inside run_sim.py (its helpers: key, type_text, home, step, shot, walk, app, S ...).  Keyboard: every entry of
# every menu (and on the screen it opens: DOWN twice, ENTER), every group and every setting of Personalize (opened and
# left), each item of each list, the clock's TAB menu and CTRL+J, the notifications.  Touch: every menu, every screen
# and every button on it.  Each picture is named after where it was taken.
import os
import time
from appconfig import cfg

TOUCH = (os.getenv("SQUIRREL_SIM_TOUCH") if hasattr(os, "getenv") else None) == "1"
_n = [0]


def snap(name):
    _n[0] += 1
    safe = "".join(c if (c.isalpha() or c.isdigit() or c in "-_") and ord(c) < 128 else "_" for c in name)
    shot("%03d-%s" % (_n[0], safe[:60]))


def sample_data():
    st = app.storage
    st.save_item("todo", "Shopping", "Shopping\n> milk\n> bread\nremember the bag")
    st.save_item("todo", "Call Tom", "Call Tom\nabout the trip on Sunday, and a much longer line that has to wrap on the screen")
    st.save_item("notes", "Ideas", "Ideas\nA bird feeder with a camera.\nPomodoro on the watch, too.")
    st.save_item("mind", "feeder", "feeder on the balcony")
    day = app.success_log.today()
    if day:
        app.success_log.save(day, day + "\n- called mum\n- fixed the bike\nok day")
    r = app.routines.create()
    r["t"], r["h"], r["m"], r["d"] = "Vitamins", 8, 30, 127
    app.routines.save()


# ------------------------------------------------------------------------------------------------ keyboard

def crawl_keys():
    home()
    snap("clock")
    key("TAB")
    step(5)
    snap("clock-tab")
    key("ESC")
    key("CTRL")
    type_text("j")
    step(10)
    snap("clock-ctrl-j")
    home()
    paths = []
    walk("MAIN", [], paths, SKIP + ("PERSONALIZE",))
    for p in paths:
        S.trace.append("== visit %s ==" % (p,))
        home()
        key("ENTER")
        for index in p:
            for _ in range(index):
                key("DOWN")
            key("ENTER")
        step(40)
        name = "menu-" + "-".join(str(i) for i in p) + "-" + type(app.active_screen).__name__
        snap(name)
        if app.overlay is not None:
            continue                                   # an action's notification: seen, home() closes it
        for k in ("DOWN", "DOWN"):
            key(k)
        step(10)
        snap(name + "-down")
        if type(app.active_screen).__name__ == "SetTimeScreen":
            continue                                   # ENTER would set the clock to what DOWN made of it
        key("ENTER")
        step(30)
        snap(name + "-enter")
    crawl_personalize()
    crawl_lists()
    crawl_overlays()


def crawl_personalize():
    home()
    app.set_screen("PERSONALIZE")
    step(5)
    ps = app.active_screen
    snap("personalize")
    for g in range(len(ps._groups)):
        ps._reset_state()
        ps.g = g
        key("ENTER")
        step(5)
        group = ps._groups[g]
        snap("pers-%s" % group)
        keys = ps._keys()
        for i in range(len(keys)):
            ps.mode, ps.i = "items", i
            ps.i_top = max(0, i - 4)
            before = cfg.get(keys[i])
            key("ENTER")
            step(5)
            snap("pers-%s-%s" % (group, keys[i]))
            if ps.mode != "items":
                key("ESC")                             # out of a list / an edit without a change
                step(3)
            if cfg.get(keys[i]) != before:
                cfg.set(keys[i], before, save=False)   # a switch that flipped: back as it was
            ps.mode = "items"
        key("ESC")
        step(3)
    for group, title in (("Time", "Time settings"), ("Cuckoo", "Cuckoo clock"),
                         ("Experimental", "Experimental")):
        app.set_screen("PERSONALIZE", groups=(group,), title=title)
        step(5)
        snap("pers-restricted-%s" % group)
    home()


def crawl_lists():
    for menu in ("TODO", "NOTES", "MIND", "WINS"):
        home()
        app.set_screen("MENU", menu_name=menu)
        step(5)
        snap("list-%s" % menu)
        count = len(app.active_screen._get_current_items())
        for i in range(1, count):
            app.set_screen("MENU", menu_name=menu)
            ms = app.active_screen
            ms.selected_index, ms.scroll_offset = i, max(0, i - 4)
            key("ENTER")
            step(10)
            snap("list-%s-%d-%s" % (menu, i, type(app.active_screen).__name__))
            key("DOWN")
            step(3)
            snap("list-%s-%d-down" % (menu, i))
            key("ENTER")
            step(10)
            snap("list-%s-%d-enter" % (menu, i))
            key("ESC")
            step(5)
        app.set_screen("MENU", menu_name=menu)
        key("ENTER")                                   # + [New item] / + [Today]
        step(10)
        snap("list-%s-new" % menu)
        key("ESC")
    home()


def crawl_overlays():
    home()
    app.battery._read = lambda: 9
    app.battery._poll()
    step(400)
    snap("overlay-battery")
    key("OPT")                                         # answered: a notification is never just hidden
    step(10)
    app.battery._read = lambda: 80
    app.battery._poll()
    hg = app.hourglass()
    hg.start(1)
    step(100)
    snap("overlay-hourglass")
    key("OPT")
    step(10)
    app.scheduler._fire(app.routines.items[0], 0, int(time.time()))
    step(10)
    snap("overlay-routine")
    key("OPT")
    step(10)
    home()


# ------------------------------------------------------------------------------------------------ touch

class FakeTouch:
    """The watch's input as the app sees it: actions, and where the finger was (hw/touch_input.py)."""
    touch = True
    is_text_mode = False
    modifiers_as_keys = False
    display_modifier = None
    last_key_code = 0

    def __init__(self):
        self.queue = []
        self.tap_xy = None
        self.touch_xy = None

    def get_pressed_action(self):
        if self.queue:
            action, xy = self.queue.pop(0)
            self.tap_xy = xy
            return action, False
        return None, False

    def set_text_mode(self, on):
        self.is_text_mode = on

    def acknowledge(self):
        return True


def touch_mode():
    """The app as on a 240 x 240 touch screen."""
    import port_config
    import gfx
    import ui.touch as ut
    import M5
    from screens.menu_screen import MenuScreen
    port_config.HARDWARE = frozenset(port_config.HARDWARE | {"input.touch"})
    ut.PX_PER_MM = 220 / 25.4                          # the watch's panel (port.toml ppi)
    lcd = M5.Lcd
    lcd._can_layout = True
    lcd._layout_h = 135

    def set_layout(h):
        lcd._layout_h = h
    lcd.set_layout = set_layout
    lcd.height = lambda: lcd._layout_h
    lcd.layout_origin = lambda: 0
    gfx.PANEL_H = 240
    app.keypad = FakeTouch()
    app.screens["MENU"] = MenuScreen(app)
    for name in [n for n in app.screens if n not in ("CLOCK", "MENU")]:
        app.screens.pop(name)                          # built again, for touch


def act(action, xy=None, wait=8):
    if app.dimmer.dimmed:
        app.keypad.queue.append(("ESC", None))         # the waking touch does nothing else
        step(3)
    app.keypad.queue.append((action, xy))
    step(wait)


def tap_widgets(name):
    """Tap every widget of the screen's TouchPanel, one at a time, the screen opened again before each."""
    screen = app.active_screen
    panel = getattr(screen, "_panel", None)
    if panel is None:
        return
    count = len(panel._items)
    for n in range(count):
        items = panel._items
        if n >= len(items):
            break
        w = items[n][0]
        act("ENTER", (w.x + w.w // 2, w.y + w.h // 2), wait=15)
        snap("%s-tap%d-%s" % (name, n, getattr(w, "label", "")))


def crawl_touch():
    touch_mode()
    app.set_screen("CLOCK")
    step(5)
    snap("t-clock")
    from menu_tree import MENUS, COLLECTIONS
    for menu in list(MENUS) + list(COLLECTIONS):
        app.set_screen("MENU", menu_name=menu)
        step(5)
        snap("t-menu-%s" % menu)
        ms = app.active_screen
        for row in range(min(ms.max_visible, len(ms._get_current_items()))):
            app.set_screen("MENU", menu_name=menu)
            step(3)
            act("ENTER", (100, ms._list.y_of(row) + 4), wait=20)
            snap("t-menu-%s-row%d-%s" % (menu, row, type(app.active_screen).__name__))
            if app.active_screen is not ms:
                tap_widgets("t-menu-%s-row%d" % (menu, row))
            if app.overlay is not None:
                act("ESC")
    for name, kwargs in (("FOCUS_STATS", {}), ("HOURGLASS", {}), ("INTERVALS", {"mode": "pomodoro"}),
                         ("METRONOME", {}), ("BREATHING", {}), ("ROUTINES", {}), ("SILENT_MODE", {"channel": "sound"}),
                         ("SET_TIME", {}), ("PERSONALIZE", {}), ("BLE_SYNC", {})):
        if name not in app.screens and name not in _lazy():
            continue
        app.set_screen(name, **kwargs)
        step(10)
        snap("t-%s" % name)
        tap_widgets("t-%s" % name)
        app.set_screen("CLOCK")
        step(3)
    app.set_screen("CLOCK")


def _lazy():
    import squirrel_app
    return squirrel_app._LAZY_SCREENS


step(20)
sample_data()
step(10)
if TOUCH:
    crawl_touch()
else:
    crawl_keys()
