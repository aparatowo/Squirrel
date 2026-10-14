# Squirrel! - notes for working on the code

A calm notes / To-Do / routines assistant for people with ADHD, in MicroPython 1.25 on ESP32 devices: the M5Stack
Cardputer ADV (the main device, with a keyboard), the LilyGo T-Watch 2020 V3, and an experimental generic ESP32-S3
watch. Licence: MIT - Rafał Nitychoruk (Ijon Tichy). The documents: [docs/README.md](docs/README.md).

## Rules

- **Code, comments, docstrings, commit messages and tool output in English.** The user interface is translated (English,
  Polish, French, German): every text on screen goes through `i18n._()`; see
  [docs/implementation/en/i18n.md](docs/implementation/en/i18n.md).
- **Hardware facts live in `ports/<port>/port.toml`**, app defaults in `nuts.py`; the app hardcodes neither pins nor
  constants. The `M5` module only in `drivers/m5_*.py` and `ports/cardputer_adv/board.py`; everything else draws
  through `gfx.Lcd`.
- **One screen = one file in `screens/`**; business logic apart from the UI.
- **Every device counts:** an ESP32-S3 without PSRAM has ~160 KB of heap for everything - see
  [docs/implementation/en/performance.md](docs/implementation/en/performance.md). MicroPython lacks some CPython
  things (`str.ljust`; `"%-10s"` pads by bytes - use `charmap.pad`).
- **A refactoring must not change behaviour:** `tools/sim/compare.sh` gives an identical trace.
- **Before a commit:** the PC tests, `tools/i18n/check.py`, `build_firmware.py --stage-only` for each port
  ([docs/implementation/en/testing.md](docs/implementation/en/testing.md)).
- **Words:** in the docs the Cardputer is the *boss* of the Bluetooth sync and the watches are *nodes* (`head` in the
  code); on the screens the nodes wait for *the squirrel*, which looks for *nuts*. The text under the clock is never
  translated.
- **Not in the docs:** plans for future devices beyond the ports that exist.
- Bluetooth keys stay on the internal flash, never on a removable SD card.

## Layout (inside `Squirrel!/`)

```
squirrel_boot.py, squirrel_app.py   start-up and the app (device/main.py on the device starts squirrel_boot)
nuts.py                             app defaults and constants (no hardware facts)
appconfig.py, appconfig_schema.py   config.txt: the settings, their kinds, ranges, help
i18n.py, lang/, translations/       languages (lang/*.py generated from translations/*.tsv)
features.toml, features.py          hardware-dependent features; port_config.py is GENERATED - do not edit
ports/<port>/                       port.toml (hardware), board.py (drivers put together), firmware/ (watch builds)
drivers/                            drivers named after the chip; pins come as arguments
hw/, ui/                            device-independent hardware logic; touch widgets
screens/                            the screens
ble/                                the Bluetooth sync (protocol, merge, peripheral = node, central = boss, auth, auto)
tools/                              tests, simulator, hardware tests, i18n, fonts, the Web Bluetooth page
build_firmware.py                   builds and flashes the images (docs/implementation/en/building.md)
```

## Building

```bash
python3 build_firmware.py --install-idf          # once: ESP-IDF 5.4.2 (not 5.5: the Cardputer's mic records silence)
python3 build_firmware.py --setup                # once, Cardputer: needs quilt
python3 build_firmware.py --flash /dev/ttyACM0   # Cardputer (hold G0 while plugging in if flashing fails)
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0
```

More: [building](docs/implementation/en/building.md), [ports](docs/implementation/en/ports.md),
[Bluetooth](docs/implementation/en/bluetooth.md), [backlog](docs/implementation/en/backlog.md).
