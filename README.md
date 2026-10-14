![Squirrel!](squirrel.jpg)

# 🐿️ Squirrel!

**A big-hearted, fluffy-tailed electronic assistant that fits in your pocket - and on your wrist.**

*English · [Polski](README_pl.md) · [Français](README_fr.md) · [Deutsch](README_de.md)*

---

Squirrel! doesn't need a phone, the internet, a cloud, or AI. More importantly, it doesn't steal your attention with a
thousand notifications - the way your smartphone usually does.

They say squirrels have terrible memories. Squirrel! has enough memory for two. It remembers what you usually forget,
gently reminds you when you drift, and celebrates with you when you pull through. It never sighs, never counts how many
times you've asked the same thing, never shows you a red streak. It just comes back every day, ready to help.

It is made for people with ADHD, time blindness and executive dysfunction - and for anyone who needs a calm, patient
tool that doesn't make them feel bad for *"falling behind"*.

<img src="shots/cardputer/en/clock.png" width="360"> <img src="shots/twatch/en/clock.png" width="240">

## What makes it different

- **No penalty for missing.** Miss your morning routine and nothing turns red, no streak resets. Tomorrow the routine
  is waiting for you, unchanged, without comment.
- **Calm by design.** No popups, no badges, no competing noise. What you need is on screen; the rest stays out of the
  way.
- **Reminders on your terms.** As many routines as you need, a cuckoo every hour and, if you like, every quarter - or
  silence, at night or whenever you choose.
- **Offline and yours.** No account, no subscription, no cloud. Your notes and To-Dos are plain files on your device;
  the only radio talk is the Bluetooth sync between your own paired devices, and Wi-Fi for the time.
- **Nothing works? That's OK too.** Experiment with the tools and keep what works **for you**.

## What it does

| | |
|---|---|
| 🕐 **Clock** with the battery and today's focus as bars | 🧠 **Mind dump** - a thought out of your head in seconds |
| ✅ **To-Dos and checklists** that don't judge | 🎙️ **Voice notes** at one button |
| 📋 **Text notes**, plain `.txt` files | 🔄 **Routines** with no streak to lose |
| 🦅 **Cuckoo clock** against time blindness | 🍅 **Pomodoro and training** in the background |
| 🥁 **Metronome** and 🫁 **breathing** | 📊 **Statistics** - a quiet picture of your days |
| 🔗 **Bluetooth sync** between your devices | 🌍 **English, Polski, Français, Deutsch** |

<img src="shots/cardputer/en/checklist-ticked.png" width="360"> <img src="shots/twatch/en/pomodoro_running.png" width="240">

Screen by screen: [features](docs/guides/en/features.md) · the keys: [shortcuts](docs/guides/en/shortcuts.md).

## Devices

| Device | |
|---|---|
| **M5Stack Cardputer ADV** | the pocket computer with a keyboard - the main Squirrel!, where you write |
| **LilyGo T-Watch 2020 V3** | on your wrist: reads and ticks what the Cardputer gives it, routines and timers, vibration |
| **ESP32-S3 smartwatches** | *experimental*, not yet tried on a device |

## Getting started

```bash
git clone https://github.com/aparatowo/Squirrel.git
cd "Squirrel/Squirrel!"
python3 build_firmware.py --install-idf                     # once
python3 build_firmware.py --flash /dev/ttyACM0              # Cardputer ADV
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0     # T-Watch 2020 V3
```

All the steps: [getting started](docs/guides/en/getting-started.md).

## Read more

- **For users:** [getting started](docs/guides/en/getting-started.md) · [features](docs/guides/en/features.md) ·
  [shortcuts](docs/guides/en/shortcuts.md) · [Bluetooth sync](docs/guides/en/bluetooth.md)
- **What's new:** [release notes](docs/releases/README.md) - version 2.0: Bluetooth sync, four languages, checklists
- **For developers:** [building](docs/implementation/en/building.md) · [ports](docs/implementation/en/ports.md) ·
  [all the documents](docs/README.md)
- **Translating:** [Squirrel!/translations](Squirrel!/translations/README.md)
- **[From the author](docs/author/en.md)** - why Squirrel! exists

---

Squirrel! runs on MicroPython. Open source (MIT, [LICENSE.txt](LICENSE.txt); third-party parts:
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). Built with care. Shared freely.
