# 🐿️ Squirrel! — ports: installing and adding devices

*[Wersja polska](PORTY_PL.md)*

Squirrel! runs on several devices from one code base. Each device is a **port**: a folder `Squirrel!/ports/<name>/`
with a description of the hardware (`port.toml`) and a module that puts that hardware together for the app
(`board.py`). This document covers:

1. installing Squirrel! on a given device,
2. adding a new device when drivers for its chips already exist,
3. what `port.toml` has to contain.

Background and design rationale (Polish): [PORTING_PL.md](PORTING_PL.md). Step-by-step guide for the Cardputer ADV:
[INSTALLATION_EN.md](INSTALLATION_EN.md).

---

## 1. Supported devices

| Port (`--port`) | Device | Base firmware | Image flashed at |
|---|---|---|---|
| `cardputer_adv` (default) | M5Stack Cardputer ADV (ESP32-S3) | `cardputer-adv-micropython` — UIFlow 2 with the `M5` module | 0x0 |
| `twatch2020_v3` | LilyGo T-Watch 2020 V3 (ESP32, 16 MB flash, 8 MB PSRAM) | `micropython-esp32` — plain MicroPython v1.25.0 | 0x1000 |

What works on which device: [RELEASE_1.2_en.md](RELEASE_1.2_en.md).

---

## 2. Installing on a given device

Run every command inside `Squirrel!/`. `build_firmware.py` needs only the Python standard library.

### 2.1. Once per computer

```bash
python3 build_firmware.py --install-idf     # ESP-IDF 5.4.2 (~1 GB) into ~/esp-idf-v5.4.2
python3 build_firmware.py --check           # checks the environment, changes nothing
```

Cardputer only, once: `python3 build_firmware.py --setup` (submodules and patches of the UIFlow repository; needs
`sudo apt install quilt`). The watch needs nothing more: on the first build the script clones MicroPython v1.25.0 into
`vendor/micropython` and applies the port's patches by itself.

### 2.2. Which USB port?

```bash
ls /dev/ttyACM* /dev/ttyUSB*
udevadm info -q property -n /dev/ttyACM0 | grep ID_VENDOR_ID
```

The Cardputer reports vendor `303a` (Espressif), the T-Watch `1a86` (CH9102 chip). Close Thonny before flashing: it
holds the port.

### 2.3. Build and flash in one command

```bash
# Cardputer ADV (the default port)
python3 build_firmware.py --flash /dev/ttyACM0

# T-Watch 2020 V3
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0
```

The script builds the image (`dist/squirrel-<port>-...bin`, plus a `.txt` file listing what is in it), flashes it and
prepares the device: it writes the `main.py` that starts Squirrel!, and on the Cardputer it also disables UIFlow's
`boot.py`. The first build compiles all of ESP-IDF and takes several minutes; later builds are quicker.

Flashing keeps your data: notes, To-Dos, statistics and `config.txt`. On the Cardputer they live on the SD card; on the
watch in `/Squirrel` on the internal flash, which an image flashed at 0x1000 does not overwrite.

### 2.4. Other variants

```bash
# flash a ready image without building
python3 build_firmware.py --port twatch2020_v3 --flash-image dist/squirrel-twatch2020_v3-....bin --flash /dev/ttyACM0

# only prepare a device flashed earlier
python3 build_firmware.py --port twatch2020_v3 --setup-device /dev/ttyACM0

# build only, no flashing
python3 build_firmware.py --port twatch2020_v3
```

To avoid typing `--port` every time, save a default port in `Squirrel!/build_config.json`:

```json
{"port": "twatch2020_v3"}
```

### 2.5. A specific Squirrel! version

Releases are git tags (`1.1`, `1.2`, ...):

```bash
git fetch --tags
git checkout 1.2          # then build as in 2.3
git checkout main         # back to the latest code
```

Ports exist since 1.2; version 1.1 and older build for the Cardputer ADV only.

### 2.6. T-Watch: before the first flash

The watch ships with different software. Before overwriting it, make a full copy of the flash:

```bash
tools/hwtest/twatch_phase0.sh /dev/ttyACM0        # 16 MB, a few minutes, with an MD5 sum -> .build/hwtest/
```

Restoring the factory state: `esptool.py --chip esp32 -p /dev/ttyACM0 -b 921600 write_flash 0x0 <copy>.bin`.

---

## 3. What a port is made of

```
Squirrel!/
  features.toml          hardware-dependent features: what they need, what to hide and leave out without it
  ports/<port>/
    port.toml            the device's hardware: pins, addresses, drivers, feature choices (read on the PC only)
    board.py             puts the drivers together for the app (the only module that knows which device this is)
    firmware/            MicroPython board definition (micropython-esp32 recipe only)
    keymap.py ...        other files of the port
  drivers/               drivers named after the CHIP (st7789_fb, ft6336, pcf8563, axp202 ...); pins come as arguments
  hw/                    device-independent logic: touch -> gestures, battery, sleep, buzzer, LED, clock
  ui/                    touch widgets (ui/touch.py) shared by every touch screen
  port_config.py         GENERATED from port.toml and features.toml - do not edit by hand
```

**What happens during a build:**

1. `build_firmware.py --port X` reads `ports/X/port.toml` and `features.toml`.
2. Every section of `port.toml` is a piece of hardware; every key set to `true` is a property of it (e.g.
   `input.touch`). A feature from `features.toml` is built when the port has everything in its `requires` and the
   port's `[features]` does not switch it off.
3. `port_config.py` is written: each key becomes a constant named after its path (`[display] ppi = 220` →
   `DISPLAY_PPI = 220`, `[i2c.sys] sda = 21` → `I2C_SYS_SDA = 21`), plus `HARDWARE`, `FEATURES` and lists of what the app
   must hide (`HIDDEN_MENUS`, `HIDDEN_SCREENS`, `HIDDEN_ACTIONS`, `HIDDEN_GROUPS`, `HIDDEN_KEYS`).
4. Only the drivers named in `port.toml` (`driver = "..."`) go into the firmware, together with the `drivers/` modules
   they import; modules of features the port lacks, and the folders of other ports, are left out.
5. An import check stops the build if code imports a module that is not part of this build.

---

## 4. A new port step by step

Assumption: drivers for the device's chips are already in `drivers/` (or you write them following the interfaces in
section 6).

### Step 1 — the folder

`Squirrel!/ports/<name>/` with `__init__.py` (empty), `port.toml` and `board.py`. The folder name must equal
`[port] name`.

### Step 2 — `port.toml`

Copy the port closest in hardware and change the values. All keys: section 5. Required minimum:

```toml
[port]
name     = "my_watch"
title    = "My Watch"
mcu      = "esp32"
firmware = "micropython-esp32"
board    = "firmware"
idf      = "v5.4.2"
machine  = "My Watch"             # part of sys.implementation._machine

[display]
driver = "st7789_fb"
width  = 240
height = 240

[storage]
driver   = "flash_storage"
base_dir = "/Squirrel"
flash_root = ""
```

Confirm every hardware value (pin, address, frequency, display rotation) on the device first. The tests in
`tools/hwtest/` run over the REPL on plain MicroPython, before Squirrel! is involved; see `twatch_hw.py`.

### Step 3 — `board.py`

A module of functions the app calls in this order. It reads values from `port_config` and passes them to the drivers.
Examples: `ports/twatch2020_v3/board.py` (touch, clock with alarm, deep sleep) and `ports/cardputer_adv/board.py`
(keyboard, SD card, `M5` module).

| Function | When | Returns / does |
|---|---|---|
| `begin()` | first, in `squirrel_boot.py` | powers up and starts the display (e.g. the PMU before the panel) |
| `begin_buzzer(buzzer, quiet)` | first thing in the app | `buzzer.begin(...)`; without a buzzer `buzzer.begin(quiet=quiet)` |
| `make_storage()` | before settings are read | object with `mount()`, `remount()`, `is_mounted` |
| `make_input()` | | a keyboard, or `hw.touch_input.TouchInput(chip, ACTIONS, ...)` |
| `make_buttons()` | | `{role: button}`; roles: `"quick"` (quick recorder), `"back"` (= ESC, wakes the screen) |
| `clock_chip()` | | `(factory, name)` or `(None, None)`; `factory()` → the hardware clock object |
| `make_audio()` | | `hw.audio_manager.AudioManager(backend)`; `AudioManager(None)` = no sound |
| `power_source()` | | object with `level()`, `charging()`, `millivolts()` (each may return `None`) |
| `begin_led(led, battery)` | | `led.begin(battery=battery)` without an LED; with one, also `pin` and the driver |
| `motion_off()` | | switches the accelerometer off; returns its I2C address or `None` |
| `i2c(name)` | | the current `machine.I2C` object of bus `name`, or `None` |

Optional (the app checks whether they exist):

| Name | Purpose |
|---|---|
| `EARLY_CLOCK = True` | the clock face shows the time before the rest of the app is built (faster after a wake) |
| `arm_light_sleep_wake()` | custom light-sleep wake sources (classic ESP32: ext0/ext1), instead of `[power_mgmt] wake_pins` |
| `wake_reason()` | after a deep sleep: `"alarm"`, `"button"` or `None` — required by the `deep_sleep` feature |
| `deep_sleep(alarm, touch=None)` | sets the clock alarm (`(year, month, day, hour, minute)` or `None`), turns off the display and peripherals, `machine.deepsleep()` — required by `deep_sleep` |

Touch screen: the `ACTIONS` dictionary in `board.py` turns gestures into app actions. On the watch:

```python
ACTIONS = {"tap": "ENTER", "swipe_up": "UP", "swipe_down": "DOWN", "swipe_right": "ESC", "swipe_left": "RIGHT",
           "long": "OPT"}
```

### Step 4 — firmware

**A device with UIFlow 2 (the `M5` module)** — recipe `cardputer-adv-micropython`; `[port] board` is the base board in
the firmware repository.

**Any other ESP32** — recipe `micropython-esp32`. `ports/<name>/firmware/` (named by `[port] board`) holds the board
definition for `make BOARD_DIR=...`:

| File | Contents |
|---|---|
| `mpconfigboard.cmake` | `SDKCONFIG_DEFAULTS` (e.g. `boards/sdkconfig.base`, `sdkconfig.spiram`, `sdkconfig.240mhz`, your own `sdkconfig.board`) and `MICROPY_FROZEN_MANIFEST` |
| `mpconfigboard.h` | `MICROPY_HW_BOARD_NAME` (source of `sys.implementation._machine`, compared with `[port] machine`) and `MICROPY_HW_MCU_NAME` |
| `sdkconfig.board` | flash size, partition table, faster start-up |
| `manifest.py` | `include("$(PORT_DIR)/boards/manifest.py")` and `freeze("$(BOARD_DIR)/squirrel")` |
| `patches/*.patch` | patches to MicroPython v1.25.0, applied with `git apply` (optional) |

The script copies this folder together with the sources into `.build/board-<port>/`; the `vendor/micropython` tree is
left untouched (apart from the patches). After a change to `sdkconfig*` or `mpconfigboard.cmake` the script regenerates
`sdkconfig` by itself.

A chip other than ESP32 / ESP32-S3 (e.g. RP2040) needs a new recipe in `build_firmware.py`.

### Step 5 — features

Features switch on by themselves based on the hardware. In `[features]` you can only switch one off
(`wifi_ntp = false`) or require it (`true`). Requiring a feature the hardware cannot support stops the build with an
error.

| Feature | Needs | Without it |
|---|---|---|
| `text_edit` | `input.keyboard` | no editor for notes, To-Dos and Mind Dump |
| `notes` | `input.keyboard` | notes menu hidden |
| `key_calibration` | `input.keyboard` | no key calibration |
| `voice_notes` | `audio_in`, `storage.removable` | no recordings |
| `wifi_ntp` | `radio.wifi` | time only by hand or from the hardware clock |
| `hw_clock` | `clock` | no "Sync RTC" |
| `led` | `signal.led` | LED settings and tests hidden |
| `buzzer` | `signal.buzzer` | buzzer settings and test hidden |
| `deep_sleep` | `clock.alarm`, `power_mgmt.deep_sleep` | no `deep` sleep mode and no "Upcoming alarms" screen |

A new hardware-dependent feature is a new section in `features.toml`: `requires`, `modules` (files left out of the
build), `screens`, `menus`, `actions`, `settings` (setting groups) and `keys` (single settings).

### Step 6 — checking

```bash
python3 build_firmware.py --port my_watch --gen-port-config   # port.toml errors; port_config.py to inspect
python3 build_firmware.py --port my_watch --stage-only        # file selection, imports, mpy-cross compile
python3 build_firmware.py --gen-port-config                   # restores the Cardputer's port_config.py
python3 build_firmware.py --port my_watch --flash /dev/ttyACM0
```

The `port_config.py` next to the sources belongs to the default port (the Cardputer). After `--gen-port-config` for
another port, always restore it before committing. A build always generates its own copy and ignores the one next to
the sources.

First start: `/boot_log.txt` (watch) or `/flash/boot_log.txt` (Cardputer) shows which parts started (`[TOUCH]`,
`[RTC]`, `[POWER]` ...). Report in Thonny: `import sq_info; sq_info.report()`.

If you change shared code, check that the Cardputer still behaves the same: `tools/sim/compare.sh` compares the drawing
trace, log and files of two versions in the simulator (`tools/sim/README.md`).

---

## 5. `port.toml` — key reference

Rules:
- a section = a piece of hardware; `installed = false` in a section means it is absent (the section stays as a wiring note);
- a key set to `true` = a hardware property that features can require (`input.touch`, `clock.alarm`);
- `driver = "x"` = the file `drivers/x.py`, which must exist;
- numbers may be written as `0x38` and `400_000`.

The build checks: `[port]`, `[display]` with `driver`, `width`, `height`, `[storage]` with `base_dir`, that every driver
and `board.py` exist. Other keys are read by `board.py`, so their names are free, but sticking to the ones below keeps
ports alike.

### `[port]`
| Key | Meaning |
|---|---|
| `name` | the port folder's name |
| `title` | display name |
| `mcu` | `esp32`, `esp32s3` |
| `firmware` | recipe: `micropython-esp32` or `cardputer-adv-micropython` |
| `board` | board-definition folder in the port (`micropython-esp32`) or the UIFlow base board |
| `idf` | ESP-IDF version (`v5.4.2`) |
| `machine` | part of `sys.implementation._machine`; device preparation refuses any other device |
| `reset_lines_low` | `true` for a USB-serial bridge with auto-reset (CH9102, CP210x): DTR/RTS dropped when the REPL is opened |

### `[display]`
| Key | Meaning |
|---|---|
| `driver` | `m5_display` (M5.Lcd) or `st7789_fb` (frame buffer + sending the changed rectangle) |
| `width`, `height` | panel size in pixels |
| `layout_height` | the height that screens not yet redesigned draw for (135 = the Cardputer's layout, centred) |
| `ppi` | pixels per inch; touch targets and gestures are sized in millimetres from it |
| `fonts` | `vlw` (M5 fonts) or `bitmap` |
| `spi_id`, `sck`, `mosi`, `cs`, `dc`, `baud`, `backlight`, `madctl`, `row_offset` | panel wiring and orientation (`st7789_fb`) |

### `[i2c.<name>]`
`id`, `sda`, `scl`, `freq`. Other sections refer to a bus with `bus = "<name>"`.

### `[input]`
| Key | Meaning |
|---|---|
| `driver` | `tca8418_keypad` (keyboard) or a touch chip (`ft6336`) |
| `keyboard` | `true` = text can be typed (features `text_edit`, `notes`) |
| `touch` | `true` = full-height touch screens |
| `swap_xy`, `mirror_x`, `mirror_y` | transform from touch-chip coordinates to the picture |
| `bus`, `addr`, `int`, `rst` | wiring |

### `[buttons.<role>]`
`driver` (`gpio_button`, `axp_pek`) and e.g. `pin`. Roles: `quick`, `back`.

### `[storage]`
| Key | Meaning |
|---|---|
| `driver` | `sd_spi` or `flash_storage` |
| `removable` | `true` = a card (required by `voice_notes`) |
| `base_dir` | Squirrel!'s data folder (`/sd/Squirrel`, `/Squirrel`) |
| `flash_root` | where the internal flash is mounted: `/flash` (UIFlow), `""` (plain MicroPython) |
| `slot`, `width`, `sck`, `miso`, `mosi`, `cs`, `freq` | SD card |

### `[clock]`
`driver` (`ds1302`, `pcf8563`), `bus` or pins, `int`, `alarm = true` if the chip's alarm can wake the device.

### `[power]`
`driver` (`m5_power`, `axp202`), `bus`, `irq`.

### `[audio_out]`, `[audio_in]`
`driver` (`m5_audio`). Without these sections there is no sound and no recording.

### `[signal.led]`, `[signal.buzzer]`
LED: `driver = "ws2812"`, `pin`, `min_backlight`, `max_sum`. Buzzer or vibration motor: `driver = "pin_pulser"`, `pin`,
`pwm_freq` (0 = on/off, otherwise a tone in Hz), `installed`.

### `[motion]`
`driver` (`bmi270`, `bma423`), `bus`, `addrs` — for now the accelerometer is only switched off at start-up.

### `[radio]`
`wifi = true`.

### `[power_mgmt]`
| Key | Meaning |
|---|---|
| `wake_pins` | pins that wake from light sleep (active low) |
| `slow_cpu_hz` | CPU clock while the screen is dimmed |
| `deep_sleep` | `true` = the device can really sleep (with `clock.alarm` it enables the `deep_sleep` feature) |
| `wake_button`, `wake_alarm` | pins that wake from deep sleep: the button and the clock's INT line |

### `[features]`
`<feature> = false | true` — see step 5.

---

## 6. Driver interfaces

A new driver does not have to inherit from anything; it only needs the same calls. Described in code:
`Squirrel!/hw/ports.py`.

| Part | Required calls |
|---|---|
| display (`drivers/<x>.py` with an `lcd` object) | the M5.Lcd calls: `fillScreen`, `fillRect`, `drawRect`, `drawLine`, `fillCircle`, `drawCircle`, `drawPixel`, `drawString`, `setTextColor`, `setTextSize`, `textWidth`, `fontHeight`, `setBrightness`, `getBrightness`, `setFont` (raises without fonts); colours `0xRRGGBB`. Frame buffer: `_needs_flush = True` and `flush()`; full height for touch screens: `_can_layout = True`, `set_layout(h)`, `layout_origin()`; before a deep sleep: `sleep()` |
| touch chip | `read_point()` → `(x, y)` or `None` (`OSError` on a bus error), `reopen()`; before a deep sleep: `hibernate()`. Gestures, millimetre thresholds and transforms are done by `hw/touch_input.py` |
| keyboard | `get_pressed_action()` → `(action, modifier_changed)`, `set_text_mode(on)`, `acknowledge()` |
| button | `pressed()` — `True` once per press |
| storage | `mount()`, `remount()`, `is_mounted` |
| power | `level()`, `charging()`, `millivolts()` — `None` when unknown |
| hardware clock | `hw.rtc_base.TimeProvider`: `is_available`, `get_datetime()`, `set_datetime(dt)` (tuples like `time.localtime()`); with an alarm also `set_alarm(dt or None)`, `alarm_fired()`, `clear_alarm_flag()` |
| buzzer / vibration | a class with `set(on)` (and `pwm` for a tone), passed as `pulser` to `buzzer.begin` |

---

## 7. Known pitfalls (from the T-Watch port)

- **No REPL after opening the port**: the CH9102 bridge holds the ESP32 in reset through DTR/RTS → `reset_lines_low = true`.
- **Panic with fast SPI**: on a classic ESP32, pins outside IO_MUX limit SPI to ~26.67 MHz; use `miso=None` if the
  default MISO clashes with another pin.
- **Viper code**: `mpy-cross` needs `-march=xtensawin` (the build passes it).
- **Frozen code takes precedence** over files on the flash. `.py` files in `<flash>/apps/Squirrel` replace it only in
  DEV mode (marker file `<flash>/DEV`) — handy for quick tries without rebuilding the firmware.
- **`BUILD=` on the `make` command line** breaks the MicroPython build — do not pass it.
- **Peripherals powered by a PMU** (AXP202): the display, sound and touch may need a specific LDO at a specific voltage
  before the driver sends anything.
- **Pending interrupts** of the power or clock chip hold the INT line low and prevent waking — clear them in `begin()`.
