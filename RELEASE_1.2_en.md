# 🐿️ Squirrel! 1.2

*[Wersja polska](RELEASE_1.2_pl.md)*

Squirrel 1.2 comes to a second device: the **LilyGo T-Watch 2020 V3**, a watch with a touch screen. To make that
possible, the app code has been separated from the hardware, and each device is now a **port** described by a single
configuration file. The Cardputer ADV is now the first of these ports and works exactly as it did in 1.1. The watch can
truly sleep and wake up on its own for routines and the cuckoo clock. There are also a few fixes that apply to the
Cardputer as well.

---

## What's new

### ⌚ LilyGo T-Watch 2020 V3 port

Squirrel runs on the watch on plain MicroPython 1.25.0, without UIFlow. Everything below has been tested on the device.

**Working:**
- **Clock face:** large full-screen digits, the date, the weekday and a status line (battery, focus).
- **Touch control:**

  | Gesture | Action |
  |---|---|
  | tap | open / select (ENTER) |
  | swipe up / down | previous / next item |
  | swipe right | back (ESC) |
  | swipe left | forward (RIGHT) |
  | long press | extra action, e.g. tick a To-Do or restore a default value |
  | side button | back; on the clock face it only wakes the screen |
  | tap on the "<" header | back |

- **Touch menus:** rows about 6 mm tall, easy to hit with a finger.
- **Setting the time by touch:** + and − buttons above and below each field; holding one changes the value faster and
  faster.
- **Personalize by touch:**
  - on/off toggled with a tap;
  - colours and options picked from a list, colours with a sample;
  - numbers, times and weekdays changed with buttons.
- **To-Do:** browsing the list, viewing a task, ticking it with a long press.
- **Focus tools:** Pomodoro, Training, metronome, breathing, routines, cuckoo clock and statistics.
- **Vibration instead of a buzzer:** the vibration motor works like the 1.1 buzzer, with all its modes. It is off by
  default; turn it on in *Settings → Personalize → Buzzer*.
- **PCF8563 hardware clock:** battery-backed, so the time survives a restart.
- **Battery:** level, voltage and charging state read from the AXP202 power chip.
- **Deep sleep with clock alarms** — see below.
- **Data:** stored in the watch's internal memory (`/Squirrel`, about 14 MB); firmware updates do not erase it.

**Not working yet:**
- **Sound:** the speaker works in the hardware tests, but the app does not use it yet. Signals are vibration for now.
- **Voice notes:** the PDM microphone needs a driver that MicroPython does not have.
- **Typing:** without a keyboard you cannot create notes, To-Dos or Mind Dumps, and the notes menu is hidden. Tasks can
  be added as `.txt` files in `/Squirrel/todo`, e.g. with Thonny.
- **Time sync over Wi-Fi:** off, because the hardware clock keeps the time. Set it by hand in *Settings → Time and date
  → Set Time*.
- **Accelerometer:** switched off at start-up; a step counter and wrist gestures are planned.
- **Some screens** (silent mode, Pomodoro, Training, metronome, breathing, statistics, To-Do viewer) still use the
  Cardputer's 240×135 layout, centred on the watch screen. They will be redesigned for full height and touch one by one.

**Installation:** [PORTS_EN.md](PORTS_EN.md), section 2. In short:

```bash
cd Squirrel!
python3 build_firmware.py --install-idf                          # once
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0
```

Before the first flash, it is worth backing up the factory software: `tools/hwtest/twatch_phase0.sh /dev/ttyACM0`.

### 😴 Deep sleep with clock alarms

On a device whose hardware clock has an alarm (today the T-Watch), Squirrel can truly sleep: the screen, touch panel and
amplifier are off and the processor draws a few microamps.

- **Turning it on:** *Settings → Personalize → Power → Sleep mode* = `deep`.
- **When it sleeps:** after *Deep sleep after* minutes with the screen dimmed; 10 minutes by default, adjustable from 1
  to 120.
- **What wakes it:**
  - the side button;
  - the clock alarm, set for the next event: a routine, the cuckoo (quarters included) or a snoozed routine.
- **Alarm list:** after each event the next one is written to the clock. *Settings → Time and date → Upcoming alarms*
  shows what is coming.
- **After an alarm wake** the event happens as usual, and the watch goes back to sleep 30 seconds after the screen dims
  instead of after the full delay.
- **What is kept:** the focus timer counts the time slept, and snoozed routines keep waiting.
- **When it stays awake:** while Pomodoro, Training or the metronome is running or paused, while a notification is on
  screen, and during a sound, a signal or a time sync.
- **Speed:** the time appears about 1.7 s after waking, and the whole app is ready after about 4.4 s (previously about
  7 s).
- **Other modes:** `light` puts the processor to sleep while the screen is dimmed and wakes it with the button or a
  touch; `off` disables sleeping.

The Cardputer ADV offers only `off` and `light` for now, because the DS1302 module has no alarm. The mechanism is ready
for a clock with an alarm, should the Cardputer get one.

### 🧩 Ports: one code base, many devices

- **Device description:** each device has a folder `Squirrel!/ports/<name>/` with a `port.toml` file listing pins,
  addresses, drivers and feature choices, plus a `board.py` module.
- **Hardware-dependent features:** described in `features.toml`. A feature the device cannot support is left out of the
  firmware, and its menus, screens and settings are hidden. Examples: notes without a keyboard, recordings without a
  microphone, the LED without an LED.
- **Drivers:** named after chips (`st7789_fb`, `ft6336`, `pcf8563`, `axp202` ...), so later devices with the same chips
  can reuse them.
- **Touch in layers:** touch chip → gestures → widgets. Sizes are in millimetres, so the same interface works on another
  watch with a different screen.
- **Guide for a new device:** [PORTS_EN.md](PORTS_EN.md).

---

## Fixes (Cardputer too)

- **Weekday after setting the time by hand:** *Set Time* always saved Monday. It now saves the correct day.
- **Clock set back on save:** *Set Time* reset the seconds even when the hour and minute were left unchanged, so the
  clock went back by up to 59 seconds. It now keeps the current time when only the date changed, or nothing did.
- **"Restart to apply":** after changing *Use font*, a notice says the font changes after a restart.
- **Quick recording on a fresh card:** G0 on a newly formatted card gave "rec error" until something was recorded from
  the menu. The recordings folder is now created automatically.

---

## Other changes

- **Sleep setting:** *Light sleep* (on/off) has been replaced by *Sleep mode* with `off`, `light` and (where available)
  `deep`. The old setting is carried over automatically.
- **`config.txt`** is not read again if it has not changed since the last read.
- **Installation guides:** step 5 now describes the automatic device preparation instead of uploading files by hand.

---

## Upgrading from the previous version

- **Cardputer:** build and flash as before, `python3 build_firmware.py --flash PORT`. After flashing, the script prepares
  the device by itself (`main.py`, UIFlow's `boot.py`, the boot option).
- **Settings:** `config.txt` is kept. `POWER_LIGHT_SLEEP = true` becomes `POWER_SLEEP = light`, and `false` becomes
  `off`.
- **Files in `/flash/apps/Squirrel`:** if you uploaded `.py` files there following the old guide, you can delete them.
  The firmware uses its built-in code; files in that folder are used only in DEV mode.
- **Notes, tasks, recordings and statistics** are unchanged.

---

## For firmware builders

- **`--port NAME`** selects the device; the default is `cardputer_adv`, and it can also be set in `build_config.json`
  (`{"port": "..."}`).
- **A second firmware recipe, `micropython-esp32`:**
  - plain MicroPython v1.25.0, cloned automatically into `vendor/micropython`;
  - board definition kept in the port (`ports/<port>/firmware/`, built with `BOARD_DIR`);
  - port patches applied with `git apply`;
  - image flashed at 0x1000.
- **Faster watch start-up:**
  - CPU at 240 MHz;
  - no PSRAM test at every start;
  - quiet bootloader;
  - frozen code first in `sys.path`.

  After a board configuration change, the script regenerates `sdkconfig` by itself.
- **`--gen-port-config`** writes `port_config.py` from `port.toml`. The copy next to the sources belongs to the
  Cardputer.
- **`--setup-device PORT`** prepares a device without flashing; after `--flash` this happens automatically
  (`--no-device-setup` turns it off).
- **REPL client:**
  - raw-paste mode with flow control (the watch's slow UART);
  - an option to drop DTR/RTS for bridges with auto-reset (`[port] reset_lines_low`).
- **Import and compile checks:** cover every package; viper code is compiled with `-march=xtensawin`.
- **`tools/sim/`:** a simulator, i.e. the app under the MicroPython unix port with fake hardware. `compare.sh` compares
  two versions (drawing trace, log, files). Every change in this release produced the same trace on the Cardputer as
  version 1.1.
- **`tools/hwtest/`:** hardware tests run over the REPL, with instructions on the device's screen: the T-Watch (display,
  touch, button, vibration, speaker, clock, battery) and the accelerometers of both devices. Results:
  `tools/hwtest/README_PL.md`.
- **Removed:** the old top-level `main.py` (it bypassed `squirrel_boot`); the launcher is `device/main.py`.

---

## Known limitations

- **T-Watch:** see "Not working yet" above.
- **The *Time and date* menu on the watch** shows "Sync RTC (DS1302)", although the watch has a PCF8563. The entry reads
  the time from the PCF8563; only the label is misleading.
- **The *Silent mode* menu** shows the Buzzer and LED channels even on devices that do not have them.
- **Sleep and the USB console:** in `light` and `deep` modes a sleeping device does not answer the REPL (the Cardputer
  also disappears from USB). To work with Thonny, set *Sleep mode* = `off`.
- **The Cardputer limitations from 1.1** (LED and backlight, unknown charging state, flashing while the app runs) still
  apply.
