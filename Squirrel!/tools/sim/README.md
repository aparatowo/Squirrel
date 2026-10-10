# tools/sim — Squirrel! on the PC, with fake hardware

Runs the whole app under the **MicroPython unix port** (the same MicroPython as the firmware), with fakes of `M5`,
`machine`, `esp32`, `network` ... (`fakes/`), a clock that only moves when the code sleeps, and the device's `/sd` and
`/flash` mapped into a folder.  A fixed scenario (`run_sim.py`) visits every menu entry, writes a To-Do, a note and a
Mind Dump, records and plays a voice note, runs the focus timer and a Pomodoro, and idles.  Everything the app draws,
logs and writes is recorded.

The point: **a refactoring that does not change behaviour gives an identical trace.**  That is how the ports
refactoring (stage 0 of `PORTING_PL.md`) was checked before it reached a device.

## Once: build the MicroPython unix port

From the firmware repository (`vendor/cardputer-adv-micropython` or wherever `--repo` points), into any folder:

```bash
cd <firmware repo>/micropython
make -C ports/unix BUILD=$HOME/mp-unix PROG=micropython \
     MICROPY_PY_FFI=0 MICROPY_PY_BTREE=0 MICROPY_PY_SSL=0 MICROPY_SSL_AXTLS=0 MICROPY_SSL_MBEDTLS=0 -j8
# -> $HOME/mp-unix/micropython
```

## Compare two versions

```bash
# the baseline = the last commit (or any other)
mkdir -p /tmp/base && git archive HEAD "Squirrel!" | tar -x -C /tmp/base
# run both and compare (from the folder with squirrel_app.py)
tools/sim/compare.sh $HOME/mp-unix/micropython "/tmp/base/Squirrel!" "$PWD" /tmp/simwork
```

It prints `IDENTICAL` / `DIFFERENT` for the display trace, the console log, `boot_log.txt` and the files on `/sd` and
`/flash` (lines that only state the free heap are ignored: they depend on the size of the code).  The traces and logs
stay in the work folder (`trace_a.txt`, `out_a.txt` ...) for a `diff`.

## Run once

```bash
mkdir /tmp/root && $HOME/mp-unix/micropython -X heapsize=8M tools/sim/run_sim.py "$PWD" /tmp/root /tmp/trace.txt
```

The app folder needs a `port_config.py` (`python3 build_firmware.py --gen-port-config [--port NAME]`); the folder of a
staged build (`.build/stage` after `--stage-only`) works too, and so shows what a port without some features does.

## What it does not test

The hardware itself (timing of the SD card, the I2C bus, the LED, sound), the real heap of the ESP32 (the unix port
compiles the `.py` files into RAM and has 64-bit objects), Wi-Fi.  Those need the device.
