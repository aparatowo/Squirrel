# tools/sim/shots_scenario.py - the Cardputer's screens worth a picture, for the guides (docs/guides/<lang>/)
#
#   SQUIRREL_SIM_SCENARIO=tools/sim/shots_scenario.py micropython tools/sim/run_sim.py <app> <work> <trace>
#   python3 tools/sim/render_shots.py <trace> shots/cardputer/<lang>
# Runs inside run_sim.py (its helpers: key, type_text, home, step, shot, app ...).  Each shot("name") becomes
# <name>.png.  The language is the one of the work dir's config.txt (LANGUAGE=...), so the same scenario gives the
# pictures of every language.  The data shown (a shopping checklist, routines, a note) is put in first, in that
# language too.
import time
from appconfig import cfg


def go(path, wait=20):
    """From the clock: the main menu, then ENTER on each entry of `path` (indexes), as a user would."""
    home()
    key("ENTER")
    for index in path:
        for _ in range(index):
            key("DOWN")
        key("ENTER")
    step(wait)


def delete_key():
    """DEL: FN, then Backspace (the Cardputer has no DEL key)."""
    key("FN")
    key("BACKSPACE")


def pick(text):
    """In the list on screen: down to the first row that contains `text`, and open it."""
    rows = app.active_screen._get_current_items()
    for n, row in enumerate(rows):
        if text in row:
            for _ in range(n - app.active_screen.selected_index):
                key("DOWN")
            key("ENTER")
            step(10)
            return
    S.trace.append("PICK: no row with %r in %r" % (text, rows))


# The data on the screens, in the language of the pictures: (shopping title, its lines, To-Do title, its line,
# note title, its lines, three routines, the item typed in, the thought for the mind dump)
SAMPLES = {
    "en": ("Saturday shopping", ("milk", "bread", "nuts", "remember the bag"), "Call Tom", "about the trip on Sunday",
           "Ideas", ("A bird feeder with a camera.", "Pomodoro on the watch, too."),
           ("Vitamins", "Stretching", "Water the plants"), "buy sunflower seeds", "feeder on the balcony"),
    "pl": ("Zakupy na sobotę", ("mleko", "chleb", "orzechy", "pamiętaj o torbie"), "Zadzwoń do Tomka",
           "w sprawie niedzielnej wycieczki", "Pomysły", ("Karmnik dla ptaków z kamerą.", "Pomodoro także na zegarku."),
           ("Witaminy", "Rozciąganie", "Podlej kwiatki"), "kup słonecznik", "karmnik na balkonie"),
    "fr": ("Courses du samedi", ("lait", "pain", "noix", "ne pas oublier le sac"), "Appeler Tom",
           "pour la sortie de dimanche", "Idées", ("Une mangeoire avec une caméra.", "Le Pomodoro sur la montre aussi."),
           ("Vitamines", "Étirements", "Arroser les plantes"), "acheter des graines", "mangeoire au balcon"),
    "de": ("Einkauf am Samstag", ("Milch", "Brot", "Nüsse", "Tasche nicht vergessen"), "Tom anrufen",
           "wegen des Ausflugs am Sonntag", "Ideen", ("Ein Vogelhaus mit Kamera.", "Pomodoro auch auf der Uhr."),
           ("Vitamine", "Dehnen", "Blumen gießen"), "Sonnenblumenkerne kaufen", "Vogelhaus auf dem Balkon"),
}
(SHOP, SHOP_LINES, CALL, CALL_LINE, NOTE, NOTE_LINES, ROUTINES, NEW_ITEM,
 THOUGHT) = SAMPLES.get(cfg.get("LANGUAGE"), SAMPLES["en"])
cfg.set("KEYBOARD_LAYOUT", "de" if cfg.get("LANGUAGE") == "de" else "pl", save=False)   # ALT+letter: ä / ą
app.storage.save_item("todo", SHOP, "\n".join((SHOP,) + tuple("> " + t for t in SHOP_LINES[:-1]) + SHOP_LINES[-1:]))
app.storage.save_item("todo", CALL, CALL + "\n" + CALL_LINE)
app.storage.save_item("notes", NOTE, "\n".join((NOTE,) + NOTE_LINES))
for text, h, m, days in zip(ROUTINES, (8, 17, 19), (30, 0, 0), (127, 31, 64 | 1)):
    r = app.routines.create()
    r["t"], r["h"], r["m"], r["d"] = text, h, m, days
app.routines.items[2]["on"] = False                 # one switched off: the list shows it so
app.routines.save()
step(10)

home()
shot("clock")
key("TAB")
step(5)
shot("tab-menu")
key("ESC")
home()
key("ENTER")
step(5)
shot("menu-main")

go([0])
shot("menu-focus-tools")
go([2])
shot("todo-list")
pick(SHOP)
shot("checklist")
key("DOWN")
key("OPT")
step(5)
shot("checklist-ticked")
go([2])
key("ENTER")                    # the first row, "+ [New item]" (in any language)
step(10)
type_text(NEW_ITEM)
step(5)
shot("editor")
key("ESC")
key("ESC")

home()
key("TAB")
type_text("m")
type_text(THOUGHT)
step(5)
shot("mind-dump")
key("ENTER")
step(20)

go([1])
shot("menu-notes")
go([1, 0])
pick(NOTE)
shot("note-viewer")
delete_key()
step(5)
shot("delete-confirm")
key("ESC")

go([0, 1])
shot("routines")
key("ENTER")
step(5)
shot("routine")
home()
app.scheduler._fire(app.routines.items[0], 0, int(time.time()))
step(10)
shot("routine-due")
key("OPT")
step(10)

go([0, 2])
shot("pomodoro")
key("ENTER")
step(200)
shot("pomodoro-running")
delete_key()
step(10)
go([0, 4])
shot("training")
key("RIGHT")
step(5)
shot("training-blocks")
key("ESC")
go([0, 3])
key("ENTER")
step(30)
shot("metronome")
key("ENTER")
go([0, 5])
key("ENTER")
step(120)
shot("breathing")
key("ENTER")
go([0, 6])
shot("statistics")

go([3])
shot("menu-settings")
go([3, 0])
shot("personalize")
key("ENTER")
step(5)
shot("personalize-display")
for _ in range(5):
    key("DOWN")
key("ENTER")
step(5)
shot("personalize-language")
key("ESC")
go([3, 3])
shot("bluetooth")
home()
key("Aa")
step(15)
shot("quick-sync")
step(150)
go([3, 4])
shot("silent-mode")
go([3, 2])
shot("time-and-date")
go([3, 2, 3])
shot("set-time")
go([3, 1, 0])
shot("wifi-networks")
go([1, 2])
shot("voice-notes")
key("ENTER")
step(10)
shot("recorder")
key("ESC")
home()
