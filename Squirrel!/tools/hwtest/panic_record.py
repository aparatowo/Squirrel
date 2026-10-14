# tools/hwtest/panic_record.py - what the last panic of the Cardputer left in RTC memory (firmware_patches/0002-panic-record.patch)
#
# The Cardputer's console is TinyUSB, so a panic's own output is lost; the firmware keeps the reason, the task and the
# backtrace in RTC memory over the restart - and, when another task panicked (the watchdog of squirrel_app.run: a
# frozen main loop), where the main task was.  This reads them over the REPL and names the functions (addr2line on the
# firmware's ELF).  From the folder with squirrel_app.py:
#     python3 tools/hwtest/panic_record.py /dev/serial/by-id/usb-M5Stack...      [--elf FILE] [--clear]
import argparse
import glob
import os
import struct
import subprocess
import sys

sys.path.insert(0, ".")
import build_firmware as bf

MAGIC = 0x5351504E
WORDS = 8 + 24 + 4 + 24 + 1 + 24         # squirrel_panic_t
TWDT_WORDS = 2 + 4 + 1 + 24               # squirrel_twdt_t: the task watchdog's interrupt (on core 0)
EXCEPTIONS = ["debug", "interrupt watchdog", "task watchdog", "abort", "fault"]
CAUSES = {0: "IllegalInstruction", 2: "InstructionFetchError", 3: "LoadStoreError", 6: "IntegerDivideByZero",
          9: "LoadStoreAlignment", 20: "InstFetchProhibited", 28: "LoadProhibited", 29: "StoreProhibited"}


def tool(name):
    found = sorted(glob.glob(os.path.expanduser("~/.espressif/tools/xtensa-esp-elf/*/xtensa-esp-elf/bin/xtensa-esp32s3-elf-" + name)))
    if not found:
        raise SystemExit("xtensa-esp32s3-elf-%s not found under ~/.espressif (ESP-IDF tools)" % name)
    return found[-1]


def default_elf():
    found = glob.glob(os.path.expanduser("~/src/cardputer-adv-micropython/m5stack/build-*_Squirrel/micropython.elf"))
    return max(found, key=os.path.getmtime) if found else None


def names(elf, addrs):
    out = subprocess.check_output([tool("addr2line"), "-pfiaC", "-e", elf] + ["0x%08x" % x for x in addrs], text=True)
    return "\n".join("  " + l for l in out.strip().splitlines())


def show_twdt(text, elf):
    """The record of the task watchdog's interrupt: the core it ran on and what that core was doing."""
    if not text:
        return
    raw = struct.pack("<%dI" % TWDT_WORDS, *eval(text.strip().splitlines()[-1]))
    magic, core = struct.unpack_from("<2I", raw)
    if magic != MAGIC:
        return
    task = raw[8:24].split(b"\0")[0].decode(errors="replace")
    depth = struct.unpack_from("<I", raw, 24)[0]
    back = list(struct.unpack_from("<24I", raw, 28))[:min(depth, 24)]
    print("task watchdog interrupt: core %d, task %r there; from the interrupt down:" % (core, task))
    if back:
        print(names(elf, back))


def main():
    ap = argparse.ArgumentParser(description="The last panic of the Cardputer, from RTC memory.")
    ap.add_argument("port")
    ap.add_argument("--elf", default=default_elf(), help="the firmware's micropython.elf (default: the last Squirrel build)")
    ap.add_argument("--clear", action="store_true", help="clear the record after reading it")
    ap.add_argument("--lines-low", action="store_true",
                    help="keep DTR / RTS low (the T-Watch: they reset it); then also give --elf")
    a = ap.parse_args()
    if not a.elf or not os.path.exists(a.elf):
        raise SystemExit("no ELF: pass --elf")
    out = subprocess.check_output([tool("nm"), a.elf], text=True)
    addr = next((int(l.split()[0], 16) for l in out.splitlines() if l.endswith(" squirrel_panic")), None)
    twdt = next((int(l.split()[0], 16) for l in out.splitlines() if l.endswith(" squirrel_twdt")), None)
    if addr is None:
        raise SystemExit("squirrel_panic is not in %s - a build without the panic record" % a.elf)
    r = bf.RawRepl(a.port, lines_low=a.lines_low)
    r.enter()
    text = r.run("import machine\nprint([machine.mem32[0x%x + 4 * i] & 0xffffffff for i in range(%d)])" % (addr, WORDS))
    twdt_text = None
    if twdt is not None:
        twdt_text = r.run("import machine\nprint([machine.mem32[0x%x + 4 * i] & 0xffffffff for i in range(%d)])"
                          % (twdt, TWDT_WORDS))
    if a.clear:
        r.run("import machine\nmachine.mem32[0x%x] = 0" % addr)
        if twdt is not None:
            r.run("import machine\nmachine.mem32[0x%x] = 0" % twdt)
    r.write(b"\x02")
    r.close()
    show_twdt(twdt_text, a.elf)
    words = eval(text.strip().splitlines()[-1])
    raw = struct.pack("<%dI" % WORDS, *words)
    magic, count, core, exc, cause, vaddr, pc, depth = struct.unpack_from("<8I", raw)
    if magic != MAGIC:
        print("no panic recorded (since the record was cleared or the device was powered off)")
        return 0
    back = list(struct.unpack_from("<24I", raw, 32))[:min(depth, 24)]
    task = raw[128:144].split(b"\0")[0].decode(errors="replace")
    reason = raw[144:240].split(b"\0")[0].decode(errors="replace")
    print("panics recorded: %d   core %d   task %r" % (count, core, task))
    print("kind: %s   reason: %s" % (EXCEPTIONS[exc] if exc < len(EXCEPTIONS) else exc,
                                       reason or "(none given: an abort - the watchdog of squirrel_app.run, say)"))
    print("exccause %d (%s)   excvaddr 0x%08x   pc 0x%08x" % (cause, CAUSES.get(cause, "?"), vaddr, pc))
    main_depth = struct.unpack_from("<I", raw, 240)[0]
    main_back = list(struct.unpack_from("<24I", raw, 244))[:min(main_depth, 24)]
    for title, addrs in (("backtrace:", back), ("mp_task (the main task) at that moment:", main_back)):
        if addrs:
            names = subprocess.check_output([tool("addr2line"), "-pfiaC", "-e", a.elf] + ["0x%08x" % x for x in addrs],
                                            text=True)
            print(title)
            print("\n".join("  " + l for l in names.strip().splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
