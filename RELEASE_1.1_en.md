# 🐿️ Squirrel! 1.1

*[Wersja polska](RELEASE_1.1_pl.md)*

Squirrel 1.1 can now get your attention in two new ways: with a buzzer and with the Cardputer ADV's built-in RGB LED. A new quiet-hours setting keeps it from disturbing you at night. Menus remember your place, and the font with Polish characters is now part of the firmware, so it no longer needs a separate upload. The firmware build script has been fixed as well: flashing works reliably, and the device starts the new firmware on its own.

---

## What's new

### 🔔 Buzzer (optional) — working

You can solder a buzzer driven by an NPN transistor to the Cardputer ADV. It has been tested on real hardware.

- **Wiring:**
  - G13 on the EXT header, through a resistor (e.g. 1 kΩ), to the transistor's base;
  - emitter to GND;
  - buzzer between the supply and the collector;
  - an extra resistor of about 10 kΩ between the base and GND, so the buzzer stays quiet at power-on before the software takes over the pin.
- **At rest:** whenever the buzzer is silent, the pin is held low.
- **Off-limits pins:** G8 and G9 are the keyboard's I2C bus, so Squirrel refuses to use them. G5, G13 and G15 are free on the EXT header.
- **Features:** for each one you turn the buzzer on and pick a mode (by default the buzzer is off for all of them):
  - notifications,
  - Pomodoro and Training blocks,
  - metronome,
  - cuckoo clock.
- **Modes:** click, short, double, triple, long, alarm, sos or auto. Auto lets the feature choose its own signal, just as it does for the speaker: for example, one sound for a hard training block and another for a break.
- **Settings and status:** *Settings → Personalize → Buzzer*. When you pick a mode, the buzzer plays it straight away so you can hear what it sounds like.
- **Try the modes:** *Settings → Experimental → Buzzer test*.
- **Configuration in `nuts.py`:**
  - no buzzer: set `BUZZER_INSTALLED = False`;
  - passive buzzer (one without its own oscillator): set `BUZZER_PWM_FREQ` to the tone frequency, e.g. 2700.

### 🌈 RGB LED — working

Squirrel now uses the RGB LED built into the Cardputer ADV (G21); it has been tested on real hardware. The LED draws its power through the screen backlight circuit, so whenever it shows something, the backlight goes to full brightness (see *Known limitations*).

- **Notifications, Pomodoro and Training, metronome, cuckoo clock:** for each feature you pick a color and a mode: flash, double, triple, long, pulse, alarm, sos or off.
- **Breathing exercise:**
  - green, growing brighter, as you breathe in;
  - green while you hold your breath;
  - blue, slowly fading, as you breathe out.
- **Charging:** the LED blinks slowly in the color of the battery level, matching the status bars: blue, green, yellow, red. This only works on devices that report charging; the Cardputer ADV does not, so on it the charging light stays off.
- **Brightness:** adjustable, 30% by default, because the LED is very intense.
- **By default** every LED feature is off. Turn them on in *Settings → Personalize → LED*.
- **Preview:** when you pick a mode or color, the LED shows it straight away; after a brightness change it flashes white.
- **Tests:** *Settings → Experimental → LED test* has four separate tests (steady colors, blinking at different intervals, brightness in steps, smooth fading) and a *Modes* submenu to try out the modes.

### 🌙 Quiet hours

In *Settings → Silent mode* you set quiet hours separately for sound, the buzzer and the LED.

- **Hours:** 22:00 to 6:00 by default. Setting 00:00–00:00 turns quiet hours off.
- **Days of the week:** chosen the same way as for routines. A night belongs to the day it starts on: ticking Friday means quiet from Friday 22:00 until Saturday 6:00.
- **What goes quiet:** notifications, routines, the cuckoo clock and Pomodoro signals make no sound and do not blink, and the charging light stays off. The notifications themselves still appear on the screen.
- **What keeps working:** anything you start yourself, such as the metronome, the breathing exercise and the tests.
- **Clock not set:** quiet hours do nothing until the clock is set, because the device does not know what time it is.

### 🧭 Menus remember your place

**When you go back**, the item you last opened is highlighted:
- after closing a note, that note;
- after leaving the player, that recording;
- in the parent menu, the submenu you came back from.

**When you enter** a menu, the first item is highlighted, as before.

### 📊 Energy log (on by default)

Every 10 minutes Squirrel writes one line of energy data:
- battery level and voltage;
- how long the screen was dimmed and the CPU slowed down;
- how many times the device went to sleep;
- how long the LED, the speaker and the radio were in use.

- **Why:** the data will help develop the planned features, the ultra power-saving mode and the calmer screen.
- **Where:** the file `/sd/Squirrel/battery.csv` on the SD card. You can open it on a computer, for example in a spreadsheet. Events and errors go separately to `/flash/boot_log.txt` in the device's memory.
- **Privacy:** the data is never sent anywhere automatically; it stays on the device. Sharing the file with the author is entirely up to you, though any such help is greatly appreciated.
- **Cost:** one line every 10 minutes, with the device's state checked once a second, so logging uses practically no energy.
- **Turning it off:** *Settings → Personalize → Power → Battery log*.

### ✍️ Polish characters built in

The font with Polish characters is now part of the firmware image. There is no separate upload, and an update will not remove it.

---

## Other changes

- **Screen dimming:** separate settings for the clock and for all other screens, both 5 seconds by default (*Personalize → Screen*).
- **Metronome:** new beat intervals of 1/8, 1/4 and 1/2 second (alongside the existing 1, 2, 5, 30, 60 and 120 s).
- **Short recordings:** recordings shorter than one second are not saved, so an accidental press of G0 no longer leaves empty files behind.
- **Statistics:**
  - completed routines and tasks are written to the card immediately;
  - focus time is saved every 15 minutes and on every pause;
  - the history is only read when you open the statistics.
- **`config.txt`:**
  - keeps your settings across power-offs and is no longer checked every few seconds;
  - changes made to the file on a computer take effect when the screen wakes up, after *Settings → Reload config*, or after a restart.
- **Fewer flash writes:** routine events, such as moving between screens, are no longer written to the log. In DEV mode the log still records everything.
- **Menus:**
  - *Focus Tools* has a new order: Cuckoo Clock, Routines, Pomodoro, Metronome, Training, Breathing, Statistics;
  - *Settings* has a new entry: *Silent mode*;
  - *Experimental* has two new entries: *Buzzer test* and *LED test*;
  - every setting name now fits on the screen; the hints they used to carry (units, what 0 means and so on) appear once you open the setting, and as comments in `config.txt`;
  - days of the week are shown spaced out, with a dash for days that are not selected (`M T W T F - -`); the *Silent mode* menu shows them next to each entry.
- **Menu headers:** the `#` lines span the full width of the screen and the title is centered, whatever font is in use.
- **Returning from screens:** *Set Time* and *Time via WiFi* now return to *Time and date*, and *WiFi networks* to *Connections*, instead of *Settings*.

---

## Upgrading from the previous version

- **Settings:** your `config.txt` on the SD card is kept. On first start Squirrel adds the new settings to it, unless the file contains an invalid line. In that case the problem is described in the log, on lines starting with `[CONFIG]`.
- **Old dimming setting:** the `SCREEN_DIM_SECONDS` line is no longer used. It is moved to the end of the file as unrecognized and can be deleted.
- **Energy log:** your kept settings include the old default that left the log off (`BATTERY_LOG = false`). To turn it on, go to *Settings → Personalize → Power → Battery log*. A log file from the previous version is kept as `battery.old.csv`.
- **Notes, tasks, recordings and statistics** are unchanged. Focus statistics saved in the old format are read correctly.

---

## For firmware builders

- **Fixed build script (`build_firmware.py`):**
  - a device that is already in download mode before flashing (G0 held while plugging in) is no longer reset. Before, the reset took it out of that mode, the USB port disappeared and flashing failed. The script only resets when the app is running;
  - after flashing, the device is restarted with a watchdog reset, so the new firmware starts on its own. After a normal reset the ESP32-S3 stayed in download mode;
  - the font goes into the image's system partition (`/system/common/font/squirrel.vlw`);
  - the `sq_info` report also checks the `hw/` folder.
- **`hw/` package:** the modules that drive the hardware directly (keyboard, SD card, clock, audio, battery, power management, radio, buzzer and LED) now live in a new `hw/` package. When installing from plain files or working in DEV mode, upload the whole `hw/` folder, just like `screens/`. A folder with that name on the device hides the entire package built into the firmware.
- **Space:** the application partition is 95% full, with about 250 KB left.

---

## Known limitations

- **LED and backlight:** the Cardputer ADV's LED is powered by the same circuit as the screen backlight. The backlight's brightness is controlled by switching its power on and off very fast (PWM), so below full brightness the LED does not get steady power and works unreliably. That is why, while the LED shows something, Squirrel sets the backlight to full brightness, 255 (`LED_MIN_BACKLIGHT` in `nuts.py`), and with the screen dimmed an LED flash briefly lights it up. With the LED features off, the backlight behaves normally.
- **Charging state:** the Cardputer ADV does not report whether it is charging (its battery voltage is only measured by the ADC). In that case the firmware always reported "charging", so Squirrel treats the state as unknown: the charging light stays off, and the `charging` column of the battery log is left empty.
- **Flashing while the app is running:** esptool cannot always switch the device into download mode. If that happens, hold G0 while plugging in the USB cable.
- **No DS1302 module:** the clock is then set over Wi-Fi at start-up, and the device may not respond to keys for a few seconds.
