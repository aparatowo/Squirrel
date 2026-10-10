#!/usr/bin/env python3
"""run.py - runs a hardware test script on a device over its MicroPython REPL and shows the results live.

    python3 tools/hwtest/run.py PORT SCRIPT [TEST ...] [--no-reset] [--list]

PORT may be `auto`: the serial port whose USB chip has the vendor id in the script's `# USB_VENDOR: xxxx` line (the
watch's CH9102: 1a86, the Cardputer's S3: 303a) - so moving a cable to another socket needs no change.
Lines `# INCLUDE: file.py` near the top put that file of this folder in front of the script (shared helpers).

SCRIPT is a file of this folder (twatch_hw.py, twatch_accel.py, cardputer_accel.py); TEST names its test functions
(default: the script's DEFAULT list).  The first line `# EXPECT_MACHINE: <text>` of the script must be part of the device's
sys.implementation._machine, or nothing is run - so a test meant for the watch never runs on the Cardputer and the
other way round.  `# SERIAL_LINES: low` near the top: DTR / RTS are dropped after opening the port (a USB-serial chip with
an auto-reset circuit, like the watch's CH9102, otherwise holds the ESP32 in reset).  Every result line is  RESULT|<test>|PASS / FAIL / INFO / ASK / SKIP|<details>;  ASK = the person at
the device has to confirm what it did.  A copy of the output goes to .build/hwtest/<script>-<time>.log.
Standard library only (the serial port through build_firmware.RawRepl).
"""
import argparse
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, APP)
from build_firmware import RawRepl, BuildError      # noqa: E402

LOGS = os.path.join(APP, ".build", "hwtest")


def usb_vendor(port):
    """The USB vendor id (4 hex digits) of a /dev/tty* port, or None."""
    name = os.path.basename(os.path.realpath(port))
    try:
        with open(f"/sys/class/tty/{name}/device/../idVendor") as f:
            return f.read().strip()
    except OSError:
        return None


def find_port(vendor):
    import glob
    hits = [p for p in sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")) if usb_vendor(p) == vendor]
    if len(hits) != 1:
        raise BuildError(f"auto: {len(hits)} ports with USB vendor {vendor} ({', '.join(hits) or 'none'}) - name the port")
    return hits[0]


def stream_run(repl, code, log, seconds=600):
    """Execute `code` and print what it prints as it arrives.  Returns the device's error text ('' = none).

    After the code is accepted: the output, Ctrl-D, the error text, Ctrl-D."""
    import select
    repl.submit(code)
    data, repl._buf = repl._buf, b""                 # what came right after the code was accepted
    shown, end = 0, time.time() + seconds
    while data.count(b"\x04") < 2:
        if time.time() >= end:
            raise BuildError(f"the test did not finish within {seconds} s")
        ready, _w, _x = select.select([repl.fd], [], [], 0.2)
        if ready:
            data += os.read(repl.fd, 4096)
        output = data.split(b"\x04")[0].decode(errors="replace")
        if len(output) > shown:
            sys.stdout.write(output[shown:])
            sys.stdout.flush()
            log.write(output[shown:])
            shown = len(output)
    output, errors = data.split(b"\x04")[:2]
    rest = output.decode(errors="replace")[shown:]
    sys.stdout.write(rest)
    log.write(rest)
    return errors.decode(errors="replace").strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run a hardware test on a device (see the top of this file).")
    ap.add_argument("port")
    ap.add_argument("script")
    ap.add_argument("tests", nargs="*")
    ap.add_argument("--no-reset", action="store_true", help="leave the device in the REPL afterwards (default: restart it)")
    ap.add_argument("--list", action="store_true", help="only list the tests of the script")
    args = ap.parse_args(argv)

    path = args.script if os.path.isfile(args.script) else os.path.join(HERE, args.script)
    with open(path, encoding="utf-8") as f:
        source = f.read()
    m = re.match(r"#\s*EXPECT_MACHINE:\s*(.+)", source)
    if not m:
        print(f"{path}: the first line must be  # EXPECT_MACHINE: <part of sys.implementation._machine>")
        return 1
    want = m.group(1).strip()
    header = source[:600]                                  # the script's own header lines (before any include)
    v = re.search(r"^#\s*USB_VENDOR:\s*([0-9a-f]{4})", header, re.M)
    lines_low = "# SERIAL_LINES: low" in header             # the watch: drop DTR / RTS (see RawRepl)
    tests = re.findall(r"^def (t\d\d\w*)\(", source, re.M)
    for inc in re.findall(r"^#\s*INCLUDE:\s*(\S+)", header, re.M):
        with open(os.path.join(HERE, inc), encoding="utf-8") as f:
            source = f.read() + "\n" + source
    if args.port == "auto":
        if not v:
            print("auto: the script has no  # USB_VENDOR: xxxx  line - name the port")
            return 1
        try:
            args.port = find_port(v.group(1))
        except BuildError as e:
            print("ERROR: " + str(e))
            return 1
        print(f"port: {args.port} (USB vendor {v.group(1)})")
    if args.list:
        print("\n".join(tests))
        return 0
    chosen = args.tests or None
    for t in chosen or ():
        if t not in tests:
            print(f"no test {t} in {os.path.basename(path)}; there are: {', '.join(tests)}")
            return 1

    os.makedirs(LOGS, exist_ok=True)
    log_path = os.path.join(LOGS, f"{os.path.basename(path)[:-3]}-{time.strftime('%Y%m%d-%H%M%S')}.log")
    repl = RawRepl(args.port, lines_low=lines_low)
    try:
        repl.enter()
        machine = repl.run("import sys\nprint(sys.implementation._machine)").strip()
        if want not in machine:
            print(f"the device on {args.port} is {machine!r}, but {os.path.basename(path)} is for {want!r} - nothing run")
            if args.no_reset:
                repl.write(b"\x02")
            else:
                repl.reset()                           # Ctrl-C stopped its program: start it again
            return 1
        print(f"device: {machine}\nlog: {log_path}\n")
        call = "run(%r)" % (chosen,) if chosen else "run(None)"
        with open(log_path, "w", encoding="utf-8") as log:
            log.write(f"device: {machine}\nscript: {path}\ntests: {chosen or 'default'}\n\n")
            errs = stream_run(repl, source + "\n" + call + "\n", log)
            if errs:
                print("\nDEVICE ERROR:\n" + errs)
                log.write("\nDEVICE ERROR:\n" + errs + "\n")
        if args.no_reset:
            repl.write(b"\x02")
        else:
            print("\n(restarting the device)")
            repl.reset()
    except BuildError as e:
        print("ERROR: " + str(e))
        return 1
    finally:
        repl.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
