# tools/hwtest/ble_e2e.py - the Bluetooth sync end to end, on the devices, through the app's own screens
#
# Both devices connected over USB.  The watch (node) runs the whole app in its REPL with Settings -> Bluetooth open
# (its main loop is stepped, as on the device); the Cardputer (head) does the same with its Bluetooth screen and
# "Sync now".  Prints what both logged.  From the folder with squirrel_app.py:
#     python3 tools/hwtest/ble_e2e.py /dev/ttyACM1 /dev/ttyACM0        # watch port, Cardputer port
#     ... --mem              the Cardputer prints its memory every half second (MEM: the largest free block and
#                            the free total of the system heap, the Python heap's free / total)
#     ... --loop tick|render the Cardputer's loop during the sync: only the Bluetooth screen's tick, or the tick and
#                            the drawing - not the app's whole step (default; for finding what disturbs the radio)
#     ... --link             both devices also pair / encrypt the link itself (nuts.BLE_LINK_PAIRING)
#     ... --pre "CODE"       Python run on the Cardputer before the app is made (e.g. a setting switched off)
#     ... --head-files       the Cardputer runs this folder's ble/ package (uploaded to /flash/t, removed after),
#                            not its frozen one - for when it cannot be flashed (its USB console is TinyUSB)
# Both are restarted at the end (the watch hard - the app runs again; the Cardputer softly: a hard reset drops its
# USB until the cable is plugged in again).
import os
import select
import sys
import threading
import time

sys.path.insert(0, ".")
import build_firmware as bf

NODE = r'''
import time
%(pre)s
import port_config
__import__(port_config.BOARD_MODULE, None, None, ("begin",)).begin()
from squirrel_app import SquirrelApp
app = SquirrelApp()
app.set_screen("BLE_SYNC")
t0 = time.ticks_ms()
shown = None
while time.ticks_diff(time.ticks_ms(), t0) < 75000:
    app._step()
    time.sleep_ms(20)
    if app.active_screen.node is not None and app.active_screen.node.passkey and app.active_screen.node.passkey != shown:
        shown = app.active_screen.node.passkey
        print("PASSKEY", shown)
    if app.active_screen.node is not None and not app.active_screen.node.busy and time.ticks_diff(time.ticks_ms(), t0) > 5000:
        break
s = app.active_screen
print("NODE-RESULT", s._result, s.node.counts if s.node else None)
print("TODOS", app.storage.stems("todo"))
print("THE-END")
'''

HEAD = r'''
import sys, time
%(override)s
import port_config
__import__(port_config.BOARD_MODULE, None, None, ("begin",)).begin()
%(pre)s
from squirrel_app import SquirrelApp
app = SquirrelApp()
t0 = time.ticks_ms()                                       # let the Wi-Fi time sync of the start-up finish first
while getattr(app.timesync, "busy", False) and time.ticks_diff(time.ticks_ms(), t0) < 20000:
    app._step(); time.sleep_ms(20)
print("TIMESYNC done in", time.ticks_diff(time.ticks_ms(), t0), "ms")
app.set_screen("BLE_HUB")
s = app.active_screen
print("NODES", [(n["name"], n["slot"]) for n in s.peers.nodes])
if not s.peers.nodes:
    s.sel = 1; s.handle_input("ENTER")                     # Add device: scan
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 15000 and s.mode != "found":
        app._step(); time.sleep_ms(20)
    print("FOUND", s.head.found)
    s.sel = 0; s.handle_input("ENTER")                     # the first one found: add + sync
else:
    s.sel = 0; s.handle_input("ENTER")                     # Sync now
def mem():
    import esp32, gc
    info = esp32.idf_heap_info(esp32.HEAP_DATA)
    print("MEM sys largest %%d free %%d | py free %%d total %%d" %% (max(i[2] for i in info), sum(i[1] for i in info),
                                                                gc.mem_free(), gc.mem_free() + gc.mem_alloc()))
import select as _sel
poll = _sel.poll(); poll.register(sys.stdin, _sel.POLLIN)
t0 = time.ticks_ms(); last = None; asked = False; code = ""; shown = t0
LOOP = "%(loop)s"
while time.ticks_diff(time.ticks_ms(), t0) < 90000:
    if LOOP == "app":
        app._step()
    elif s.needs_refresh() and LOOP == "render":
        app._render_active()
    time.sleep_ms(20)
    if %(mem)s and time.ticks_diff(time.ticks_ms(), shown) >= 500:
        shown = time.ticks_ms(); mem()
    if s.head.need_code and not asked:      # (the head's screen takes the digits; an older screen: enter_code())
        asked = True; print("NEED-CODE")
    while poll.poll(0):                                    # the code, typed by the test from the watch's screen
        ch = sys.stdin.read(1)
        if ch.isdigit():
            code += ch
        if len(code) == 6:
            s.head.enter_code(code); code = ""
    if s.head.status != last:
        last = s.head.status; print("STATUS", last)
    if not s.head.busy and time.ticks_diff(time.ticks_ms(), t0) > 2000:
        break
print("HEAD-RESULT", s.head.status, s.head.results)
import machine
machine.WDT(timeout=60000)      # armed again: a soft restart or an app start that hangs ends in a reset and a panic record
print("THE-END")
'''


SHARED = {}


def run(port, code, lines_low, delay, out, name):
    time.sleep(delay)
    r = bf.RawRepl(port, lines_low=lines_low)
    if lines_low:                                   # the watch: a clean start (it may sit in a REPL or a deep sleep)
        import fcntl, struct, termios
        fcntl.ioctl(r.fd, termios.TIOCMBIS, struct.pack("I", termios.TIOCM_RTS))
        time.sleep(0.2)
        fcntl.ioctl(r.fd, termios.TIOCMBIC, struct.pack("I", termios.TIOCM_RTS))
        time.sleep(2.5)
    r.enter()
    r.submit(code)
    buf, end = b"", time.time() + 150
    sent = False
    while time.time() < end and b"THE-END" not in buf and b"Traceback" not in buf:
        if select.select([r.fd], [], [], 0.3)[0]:
            try:
                buf += os.read(r.fd, 4096)
            except OSError:
                break
        if b"PASSKEY " in buf and "code" not in SHARED:            # the watch shows it ...
            SHARED["code"] = buf.split(b"PASSKEY ")[-1][:6].decode()
        if b"NEED-CODE" in buf and not sent and "code" in SHARED:  # ... and the "user" types it on the Cardputer
            r.write(SHARED["code"].encode())
            sent = True
    time.sleep(0.5)
    out[name] = buf.decode(errors="replace")
    if lines_low:
        r.reset()
    else:
        r.write(b"\x04\x02\x04")                   # end the raw REPL, soft restart: the app runs again
    r.close()


OVERRIDE = """
for _m in [m for m in sys.modules if m == "ble" or m.startswith("ble.")]:
    del sys.modules[_m]
sys.path.insert(0, "/flash/t")
"""


CARDPUTER_REPO = os.path.expanduser("~/src/cardputer-adv-micropython")


def upload_ble(port):
    """Copy ble/ to /flash/t/ble on the Cardputer, file by file in 2 KB pieces (its heap is small) - compiled to .mpy
    with the firmware's mpy-cross when there is one: compiling the sources on the device grows its Python heap into
    the system RAM, and the radio then fails to start (ETIMEDOUT)."""
    import shutil
    import subprocess
    import tempfile
    mpy_cross = bf.find_mpy_cross(CARDPUTER_REPO)
    work = tempfile.mkdtemp()
    names = []
    for name in sorted(os.listdir("ble")):
        if not name.endswith(".py"):
            continue
        if mpy_cross:
            out = os.path.join(work, name[:-3] + ".mpy")
            subprocess.check_call([mpy_cross, "-o", out, "-s", "ble/" + name, "ble/" + name])
            names.append((name[:-3] + ".mpy", out))
        else:
            names.append((name, "ble/" + name))
    r = bf.RawRepl(port)
    r.enter()
    r.run("import os\nfor d in ('/flash/t', '/flash/t/ble'):\n    try:\n        os.mkdir(d)\n    except OSError:\n        pass\n")
    for name, src in names:
        data = open(src, "rb").read()
        r.run("f = open('/flash/t/ble/%s', 'wb')" % name)
        for i in range(0, len(data), 2048):
            r.run("f.write(%r)" % data[i:i + 2048])
        r.run("f.close()")
    r.write(b"\x02")
    r.close()
    shutil.rmtree(work)


def remove_ble(port):
    r = bf.RawRepl(port)
    r.enter()
    r.run("import os\nfor f in os.listdir('/flash/t/ble'):\n    os.remove('/flash/t/ble/' + f)\nos.rmdir('/flash/t/ble')\nos.rmdir('/flash/t')")
    r.write(b"\x02\x04")
    r.close()


def main(watch_port, cardputer_port, head_files=False, mem=False, loop="app", pre="", link=False):
    pre_node = "import nuts; nuts.BLE_LINK_PAIRING = True" if link else ""
    if link:
        pre = (pre + "\n" if pre else "") + pre_node
    out = {}
    if head_files:
        upload_ble(cardputer_port)
    node = threading.Thread(target=run, args=(watch_port, NODE % {"pre": pre_node}, True, 0, out, "watch"))
    head = threading.Thread(target=run, args=(cardputer_port, HEAD % {"override": OVERRIDE if head_files else "", "mem": mem, "loop": loop, "pre": pre},
                                              False, 4, out, "cardputer"))
    node.start()
    head.start()
    node.join()
    head.join()
    for name in ("cardputer", "watch"):
        print("=" * 20, name)
        keep = [l for l in out.get(name, "").splitlines()
                if l.startswith(("MEM", "[BLE]", "STATUS", "HEAD-", "NODE-", "NODES", "FOUND", "TODOS", "TIMESYNC", "PASSKEY",
                                 "NEED-CODE", "Traceback", "  File"))
                or "Error" in l or "[BLE]" in l]
        print("\n".join(keep))
    if head_files:
        time.sleep(3)
        remove_ble(cardputer_port)
    ok = "Synced 1 of 1" in out.get("cardputer", "")
    print("RESULT:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    loop = sys.argv[sys.argv.index("--loop") + 1] if "--loop" in sys.argv else "app"
    pre = sys.argv[sys.argv.index("--pre") + 1] if "--pre" in sys.argv else ""
    sys.exit(main(sys.argv[1], sys.argv[2], "--head-files" in sys.argv, "--mem" in sys.argv, loop, pre,
                  "--link" in sys.argv))
