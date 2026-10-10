# Building Squirrel! firmware

Quick reference for `build_firmware.py`. The firmware repo (`cardputer-adv-micropython`) is cloned automatically into `vendor/` on first run — no manual setup needed.

## First-time setup (once per machine)

```bash
# Install ESP-IDF 5.4.2 (~1 GB) into ~/esp-idf-v5.4.2
python3 build_firmware.py --install-idf

# Install into a custom folder
python3 build_firmware.py --install-idf ~/esp

# Init submodules, apply patches, build mpy-cross
# Requires: sudo apt install quilt
python3 build_firmware.py --setup

# Build mpy-cross only (gcc only, no ESP-IDF or quilt needed)
python3 build_firmware.py --build-mpy-cross
```

## Diagnostics

```bash
# Check the whole environment without changing anything
python3 build_firmware.py --check
```

## Building

```bash
# Full build → dist/squirrel-*.bin
python3 build_firmware.py

# Application only (micropython.bin) — not directly flashable
python3 build_firmware.py --target build

# Full build + empty /flash partition — WARNING: wipes main.py and the font
python3 build_firmware.py --target pack_all
```

## Flashing

```bash
# Build and flash in one step
python3 build_firmware.py --flash /dev/ttyACM0

# Flash an already-built image
python3 build_firmware.py --flash-image dist/squirrel-....bin

# Flash an already-built image to a specific port
python3 build_firmware.py --flash-image dist/squirrel-....bin --flash /dev/ttyACM0

# After flashing to a PORT the device is prepared by itself: /flash/main.py (device/main.py),
# UIFlow's boot.py renamed when it cannot run, UIFlow boot option = run main.py.  Only that, for a device flashed earlier:
python3 build_firmware.py --setup-device /dev/ttyACM0

# Flash without preparing the device
python3 build_firmware.py --flash /dev/ttyACM0 --no-device-setup
```

## Updates and maintenance

```bash
# Pull latest changes in vendor/cardputer-adv-micropython
python3 build_firmware.py --update-repo

# Delete dependencies.lock and managed_components (re-resolved on next build)
python3 build_firmware.py --reset-deps

# Remove .build/ and the generated board definition
python3 build_firmware.py --clean
```

## Ports (devices)

Each device is a folder `ports/<name>/` with `port.toml` (its hardware, wiring and features) and `board.py`.
The default port is `cardputer_adv`.

```bash
# Build for another port (or set "port" in build_config.json)
python3 build_firmware.py --port cardputer_adv

# Regenerate port_config.py next to the sources after editing port.toml / features.toml
python3 build_firmware.py --gen-port-config

# Check that another port's sources hang together (works for every port)
python3 build_firmware.py --stage-only --port <name>
```

See `PORTING_PL.md` for the architecture.

## Checking a refactoring without the device

`tools/sim/` runs the app on the PC under the MicroPython unix port with fake hardware and compares two versions call by
call (display, logs, files on the SD card) - see `Squirrel!/tools/sim/README.md`.

## Quick options (no full build)

```bash
# Collect sources and check compilation — no firmware produced
python3 build_firmware.py --stage-only

# Compile all modules to .mpy in dist/mpy/ (upload via Thonny)
python3 build_firmware.py --mpy

# Explain errors from the last failed build (.build/make.log)
python3 build_firmware.py --diagnose
```

## Advanced

```bash
# Use a different firmware repo location
python3 build_firmware.py --repo /other/path/cardputer-adv-micropython

# Use a specific ESP-IDF installation
python3 build_firmware.py --idf ~/esp/esp-idf-v5.4.2

# Allow ESP-IDF versions other than 5.4.x (not recommended — mic broken on 5.5.x)
python3 build_firmware.py --allow-any-idf

# Build even if the board manifest references missing files
python3 build_firmware.py --allow-missing

# Resolve flat vs screens/ conflict by picking the newer file
python3 build_firmware.py --prefer newer

# Repeat setup even if it was already completed
python3 build_firmware.py --setup --force

# Exclude a file from being frozen into the firmware (repeatable)
python3 build_firmware.py --exclude diag_touch.py
```

## Typical flow for a new contributor

```bash
python3 build_firmware.py --install-idf   # download ESP-IDF 5.4.2
python3 build_firmware.py --setup         # init submodules, patches, mpy-cross
python3 build_firmware.py --check         # verify everything is in place
python3 build_firmware.py                 # build
```

After flashing, upload via Thonny: `/flash/main.py` (from `device/main.py`) and `/flash/fonts/squirrel.vlw`.