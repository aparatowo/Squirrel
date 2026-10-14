# Getting started

*[Polski](../pl/getting-started.md) · [Français](../fr/getting-started.md) · [Deutsch](../de/getting-started.md)*

From a new device to Squirrel! on it. Version 2.0.

## The devices

| Device | What it is | What you need |
|---|---|---|
| **M5Stack Cardputer ADV** | a pocket computer with a keyboard (ESP32-S3) - the main Squirrel! device, the *boss* of the Bluetooth sync | a microSD card (FAT32) for your data |
| **LilyGo T-Watch 2020 V3** | a watch with a touch screen (ESP32) - reads and ticks what the Cardputer gives it, routines and timers on your wrist | nothing more |
| **A generic ESP32-S3 smartwatch** | *experimental*: the cheap watches sold as "ESP32-S3 smartwatch" - not yet tried on a device | its pins checked first ([ports](../../implementation/en/ports.md)) |

What works on each: the Cardputer has everything; the watch has no keyboard (it does not write notes or To-Dos - it
reads and ticks them) and no sound or microphone yet, but it vibrates, sleeps deeply and has a hardware clock.

## On your computer

- **Linux** (macOS and Windows should work, but the instructions below are for Linux), **Python 3.10+**, **git**.
- A **USB-C cable** (the watch: micro-USB) that carries data, not only charging.

```bash
git clone https://github.com/aparatowo/Squirrel.git
cd "Squirrel/Squirrel!"
python3 build_firmware.py --install-idf     # ESP-IDF 5.4.2 (~1 GB), once
python3 build_firmware.py --check           # is everything in place? (changes nothing)
```

The Cardputer needs one more step, once: `python3 build_firmware.py --setup` (it needs `sudo apt install quilt`).

## Building and flashing

Close Thonny (or anything else holding the USB port), then:

```bash
# Cardputer ADV (the default device)
python3 build_firmware.py --flash /dev/ttyACM0

# T-Watch 2020 V3
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0
```

The first build compiles all of ESP-IDF and takes several minutes; later ones are quicker. The script builds the image
(in `dist/`), flashes it and prepares the device, so Squirrel! starts by itself.

**Which port?** `ls /dev/serial/by-id/` names them: the Cardputer is `...Espressif...` or `...M5Stack...`, the watch
`...1a86...`.

**The Cardputer will not flash?** Its USB console is part of the app, and resetting it drops the USB connection. Hold
**G0** while you plug the cable in: the Cardputer then waits in download mode (black screen), and flashing works. It
starts the new firmware by itself afterwards.

**The watch for the first time:** it comes with other software. Keep a copy of it first:
`tools/hwtest/twatch_phase0.sh /dev/ttyACM0` (16 MB, a few minutes).

## The first start

- **Cardputer:** put in a microSD card (FAT32); Squirrel! makes its folder `/Squirrel` there by itself.
- **The time:** the Cardputer sets its clock over Wi-Fi at start-up - add your network in *Settings → Connections →
  WiFi networks* (a phone hotspot works; 2.4 GHz). Or set it by hand (*Settings → Time and date → Set time*), or take
  it from the watch over Bluetooth.
- **The language:** *Settings → Personalize → Display → Language* - English, Polski, Français, Deutsch.
- **The watch and the Cardputer together:** pair them once ([bluetooth.md](bluetooth.md)).

Then: [features.md](features.md) for what is there, [shortcuts.md](shortcuts.md) for the keys.

## Your data

Everything is plain files: notes and To-Dos as `.txt`, voice notes as `.wav`, statistics, routines and `config.txt`
(your settings, with a comment on each). On the Cardputer they are on the SD card in `/Squirrel`; on the watch in
`/Squirrel` on its internal flash. Flashing a new version keeps them.

Nothing leaves your device - except over the Bluetooth sync to your own paired devices, and Wi-Fi only for the time.

## Updating

```bash
cd Squirrel
git pull
cd "Squirrel!"
python3 build_firmware.py --flash /dev/ttyACM0          # (--port twatch2020_v3 for the watch)
```

A particular version: `git checkout 2.0` (releases are git tags), then build as above.

## When something goes wrong

| Problem | What to do |
|---|---|
| `port not found`, the port is busy | Close Thonny; check `ls /dev/serial/by-id/`; on Linux you may need `sudo usermod -aG dialout $USER` (log in again). |
| The Cardputer does not flash | Hold G0 while plugging the cable in (above). |
| Black screen after flashing | Unplug and plug the cable in again; check the cable carries data. |
| The app does not start | `python3 build_firmware.py --setup-device PORT` prepares the device again; in Thonny: `import sq_info; sq_info.report()`. |
| Notes are not saved (Cardputer) | Is the microSD card in, formatted as FAT32? |
| It restarts by itself now and then | A watchdog restarts a frozen device after a minute; your data stays. If it happens often, please report it. |

More for those who build and change Squirrel!: [the implementation documents](../../implementation/en/).
