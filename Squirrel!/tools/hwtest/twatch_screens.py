# tools/hwtest/twatch_screens.py - screenshots of the watch's screens, taken on the watch itself
#
# The watch's display driver (drivers/st7789_fb.py) draws into a frame buffer in RAM: this tool stops the app over
# USB, builds it again in the REPL, opens one screen after another and reads the frame buffer back (base64), then saves
# PNGs (twice the size) and one contact sheet.  Needs Pillow on the PC.  From the folder with squirrel_app.py:
#     python3 tools/hwtest/twatch_screens.py /dev/ttyACM1 [folder] [--lang pl]
# The folder is shots/twatch/<lang>/ at the top of the repository by default (the old pictures are removed first);
# --lang: the language of the screens (en by default; the watch's own setting is not changed).
# It writes a sample checklist in that language on the watch (deleted again at the end) and restarts the watch at
# the end, so the app runs again (a watch left in the REPL shows the last screenshot frozen - it is not running).
import base64
import fcntl
import os
import select
import struct
import sys
import termios
import time

sys.path.insert(0, ".")
import build_firmware as bf

# The sample To-Dos, in the language of the pictures: (checklist title, its 3 items, its plain line, To-Do title, text)
SAMPLES = {
    "en": ("Saturday shopping", ("milk", "wholemeal bread", "butter"), "remember the bag", "Call Tom",
           "about the trip on Sunday - a longer text that wraps over a few lines"),
    "pl": ("Zakupy na sobotę", ("mleko", "chleb razowy", "masło"), "pamiętaj o torbie", "Zadzwoń do Tomka",
           "w sprawie niedzielnej wycieczki - dłuższy tekst, który zawija się w kilku wierszach"),
    "fr": ("Courses du samedi", ("lait", "pain complet", "beurre"), "ne pas oublier le sac", "Appeler Tom",
           "pour la sortie de dimanche - un texte plus long, sur plusieurs lignes"),
    "de": ("Einkauf am Samstag", ("Milch", "Vollkornbrot", "Butter"), "Tasche nicht vergessen", "Tom anrufen",
           "wegen des Ausflugs am Sonntag - ein längerer Text über mehrere Zeilen"),
}

SCRIPT = r'''
import gc, ubinascii, time
import port_config
__import__(port_config.BOARD_MODULE, None, None, ("begin",)).begin()
from squirrel_app import SquirrelApp
app = SquirrelApp()
from appconfig import cfg
cfg.set("LANGUAGE", "%(lang)s", save=False)
from drivers.st7789_fb import lcd
def shot(name):
    app._render_active()
    gc.collect()
    print("SHOT-BEGIN", name)
    mv = memoryview(lcd.buf)
    for i in range(0, len(mv), 3072):
        print(ubinascii.b2a_base64(mv[i:i + 3072]).decode().strip())
    print("SHOT-END")
def go(name, **kw):
    try:
        app.set_screen(name, **kw)
    except Exception as e:
        print("ERR", name, e)
todo = app.todo_editor
SHOP, ITEMS, NOTE, CALL, CALL_TEXT = %(sample)s
if "shopping_test" in app.storage.stems("todo"):        # left by an older version of this tool
    app.storage.delete_item("todo", app.storage.stems("todo").index("shopping_test"))
before = app.storage.stems("todo")
app.storage.save_item("todo", SHOP, "\n".join([SHOP] + ["> " + t for t in ITEMS[:2]] + [NOTE, "> " + ITEMS[2]]))
stems = app.storage.stems("todo")
ci = [n for n, st in enumerate(stems) if st not in before][0]
todo.toggle_item(ci, ITEMS[1], "2026-10-12")
go("CLOCK"); shot("clock")
go("MENU", menu_name="MAIN"); shot("menu_main")
go("MENU", menu_name="SETTINGS"); shot("menu_settings")
go("MENU", menu_name="TODO"); shot("menu_todo")
go("CHECKLIST", file_index=ci, title=SHOP); shot("checklist")
go("VIEWER", title=CALL, content=CALL + "\n" + CALL_TEXT, file_index=0, menu_name="TODO"); shot("viewer")
go("ROUTINES"); shot("routines")
go("INTERVALS", mode="pomodoro"); shot("pomodoro_idle")
app.runner().start(app.active_screen.plan, "Pomodoro"); time.sleep(2); shot("pomodoro_running")
app.runner().toggle(); shot("pomodoro_paused")
app.runner().stop()
go("METRONOME"); shot("metronome")
go("BREATHING"); shot("breathing_idle")
s = app.active_screen; s._toggle(); s._full = True; time.sleep(1.5); shot("breathing_running"); s._toggle()
go("FOCUS_STATS"); shot("focus_stats")
go("SET_TIME"); shot("set_time")
go("MENU", menu_name="TIME_DATE"); shot("menu_time_date")
go("MENU", menu_name="SILENT"); shot("menu_silent")
go("SILENT_MODE", channel="sound"); shot("silent_sound")
go("ALARMS"); shot("alarms")
go("PERSONALIZE", groups=("Cuckoo",), title="Cuckoo clock", back=("MENU", {"menu_name": "FOCUS"})); shot("personalize_cuckoo")
go("MENU", menu_name="FOCUS"); shot("menu_focus")
go("BLE_SYNC"); shot("ble_sync")
app.active_screen.on_exit()
go("PERSONALIZE"); shot("personalize")
app.storage.delete_item("todo", ci)                   # the sample goes: the watch keeps only its own To-Dos
print("ALL-DONE")
'''


def main(port, out, lang="en"):
    from PIL import Image, ImageDraw
    os.makedirs(out, exist_ok=True)
    for old in os.listdir(out):
        if old.endswith(".png"):
            os.remove(os.path.join(out, old))
    r = bf.RawRepl(port, lines_low=True)
    fcntl.ioctl(r.fd, termios.TIOCMBIS, struct.pack("I", termios.TIOCM_RTS))      # reset: a clean start
    time.sleep(0.2)
    fcntl.ioctl(r.fd, termios.TIOCMBIC, struct.pack("I", termios.TIOCM_RTS))
    time.sleep(2.5)
    r.enter()
    r.submit(SCRIPT % {"lang": lang, "sample": repr(SAMPLES.get(lang, SAMPLES["en"]))})
    buf, end = b"", time.time() + 600
    while time.time() < end:
        if select.select([r.fd], [], [], 0.5)[0]:
            try:
                buf += os.read(r.fd, 65536)
            except OSError:
                pass
            if b"ALL-DONE" in buf or b"Traceback" in buf[-3000:]:
                time.sleep(1)
                try:
                    buf += os.read(r.fd, 65536)
                except OSError:
                    pass
                break
    text = buf.decode(errors="replace")
    with open(os.path.join(out, "log.txt"), "w") as f:            # everything the watch printed, screenshots aside
        f.write("\n".join(l for l in text.splitlines() if len(l) < 200))
    for line in text.splitlines():
        if line.startswith("ERR") or "Traceback" in line or "Error" in line:
            print(line)
    names = []
    for part in text.split("SHOT-BEGIN ")[1:]:
        name, _, rest = part.partition("\n")
        name = name.strip()
        try:
            raw = b"".join(base64.b64decode(l) for l in rest.split("SHOT-END")[0].split() if l.strip())
        except ValueError:                                          # a character lost on the serial line
            print("damaged on the way", name)
            continue
        if len(raw) != 240 * 240 * 2:
            print("bad size", name, len(raw))
            continue
        img = Image.new("RGB", (240, 240))
        px = img.load()
        for i in range(240 * 240):
            v = (raw[2 * i] << 8) | raw[2 * i + 1]                  # RGB565, big-endian (as the panel wants it)
            px[i % 240, i // 240] = (((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2, (v & 31) << 3)
        img.resize((480, 480), Image.NEAREST).save("%s/%s.png" % (out, name))
        names.append(name)
    if names:
        cols = 4
        sheet = Image.new("RGB", (cols * 250, ((len(names) + cols - 1) // cols) * 270), (60, 60, 60))
        d = ImageDraw.Draw(sheet)
        for n, name in enumerate(names):
            x, y = (n % cols) * 250 + 5, (n // cols) * 270 + 20
            sheet.paste(Image.open("%s/%s.png" % (out, name)).resize((240, 240)), (x, y))
            d.text((x, y - 15), name, fill=(255, 255, 0))
        sheet.save("%s/sheet.png" % out)
    print("saved %d screenshots in %s" % (len(names), out))
    r.reset()                                                       # the app runs again
    r.close()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    lang = "en"
    if "--lang" in args:
        lang = args[args.index("--lang") + 1]
        del args[args.index("--lang"):args.index("--lang") + 2]
    default = os.path.join(os.path.dirname(os.path.abspath(".")), "shots", "twatch", lang)
    main(args[0], args[1] if len(args) > 1 else default, lang)
