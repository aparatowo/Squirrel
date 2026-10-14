# tools/hwtest - hardware tests (T-Watch 2020 V3, accelerometers)

Scripts that run **on the device**, through its REPL; `run.py` starts them from the PC and shows the results live.
Every result line: `RESULT|test|PASS / FAIL / INFO / ASK / SKIP|details`. **ASK** = you confirm what you saw, heard or
felt. A log of every run: `.build/hwtest/<script>-<time>.log`. The other tools of this folder (screenshots, the
Bluetooth end-to-end test, the panic record): [docs/implementation/en/testing.md](../../../docs/implementation/en/testing.md).

```bash
python3 tools/hwtest/run.py PORT SCRIPT [TEST ...]      # no TEST: the script's default set
python3 tools/hwtest/run.py PORT SCRIPT --list          # the tests
```

Safety: the script's first line (`# EXPECT_MACHINE: ...`) must match the device's `sys.implementation._machine`, or
nothing runs. The watch's tests also check that an AXP202 answers on I2C 21/22 - on another board they do nothing.
Close Thonny first (it holds the port). `PORT` may be `auto` (found by the USB vendor id: the watch's CH9102 `1a86`,
the Cardputer's S3 `303a`).

---

## T-Watch 2020 V3

### Phase 0 - read only (nothing is written to the watch)

```bash
tools/hwtest/twatch_phase0.sh PORT
```

The chip and flash id (esptool `chip_id`, `flash_id`), then a **full copy of the flash** (16 MB, a few minutes) with
its MD5 to `.build/hwtest/twatch-backup-<MAC>-<time>.bin`. That copy restores the watch's factory firmware 1:1:
`esptool.py --chip esp32 -p PORT -b 921600 write_flash 0x0 <file>`.

### Phase 1 - MicroPython (writes the whole flash)

The tests of phases 2-3 run on plain MicroPython for an ESP32 with PSRAM (board `ESP32_GENERIC`, variant `SPIRAM`),
without Squirrel!'s code: version **1.25.0**, from micropython.org/download/ESP32_GENERIC, or built locally.
Flashing: `esptool.py --chip esp32 -p PORT erase_flash`, then `write_flash -z 0x1000 <image>`.

### Phase 2 - bringing up the hardware: `twatch_hw.py`

| Test | What it does / changes | What you confirm |
|---|---|---|
| `t01_system` | reads: version, CPU, memory (PSRAM?), flash size | - |
| `t02_i2c` | scans both buses: AXP202 0x35, BMA423 0x19, PCF8563 0x51 / touch FT6336 0x38 | - |
| `t03_axp` | reads the AXP202: USB, battery, charging, which outputs are on, their voltages, the button power-off time | - |
| `t08_rtc` | reads the PCF8563: date and time, the "time invalid" bit, whether it runs | - |
| `t13_mic` | whether `machine.I2S` has PDM (the V3's microphone) | - |
| `t04_backlight` | turns on LDO2 (after checking it is set to 3.0-3.3 V), PWM on GPIO15: 3 pulses | **did the backlight pulse** |
| `t04b_backlight_pin12` | the same on GPIO12 (in case the V3 had the backlight of the V1) | as above |
| `t05_display` | ST7789: fills RED, GREEN, BLUE, WHITE (1.5 s each), then markers | **colours in this order? a yellow square top left, cyan bottom right, a red bar at the top? a band of noise?** |
| `t06_display_rot180` | the same rotated by 180° (an 80-row offset) | as above - which variant is right |
| `t07_touch` | 15 s of touch readings (start: 1 vibration, end: 2) | tap top left, top right, bottom left, bottom right, centre - **do the coordinates match** |
| `t09_vibration` | GPIO4: 3 short, 1 long | **did you feel it** |
| `t10_button` | the button's interrupt in the AXP202, 12 s (start: 1 vibration) | 2× short, 1× ~2 s - **never longer than 3 s** (that switches the watch off) |
| `t11_speaker` | turns on LDO3 (after checking its voltage), I2S: two quiet tones, then LDO3 off again | **did you hear a low and a higher tone** |
| `t12_battery` | turns on the AXP202's ADCs, reads the battery voltage, USB, currents, the % gauge | - |

Without tests named, `run.py` runs only the reading ones (`t01 t02 t03 t08 t13`). Only these AXP202 registers may be
written: 0x12 (the LDO2 / LDO3 bits), 0x82 (ADC), 0x42 / 0x4A (the button's interrupt) - a list in the code, any other
write fails the test. The voltages and supply of the ESP32 itself (DCDC2 / DCDC3) are only read.

Suggested order: `t01…t03, t08, t13` → `t04` (or `t04b`) → `t05`, `t06` → `t09` → `t07` → `t10` → `t11` → `t12`.

### Phase 3 - the accelerometer: `twatch_accel.py`

Hints by vibration (the screen may not work yet): **1 short** = take the next position (6 s), **2 short** = measured,
**3 short** = shake.

| Test | What you do |
|---|---|
| `t01_identify` | - (chip id BMA423 = 0x13) |
| `t02_still` | the watch flat, face up |
| `t03_orientation` | 1) face up, 2) face down, 3) upright, "12" at the top, 4) on its side, button up |
| `t04_shake` | shake for 5 s |
| `t05_temperature` | - |
| `t06_off` | - (the accelerometer switched off again) |

Only the bare accelerometer: the step counter, wrist-raise and double-tap detection need a configuration file
(~6 KB) loaded into the chip first.

---

## Cardputer ADV - the accelerometer: `cardputer_accel.py`

```bash
python3 tools/hwtest/run.py PORT cardputer_accel.py
```

Runs on Squirrel!'s firmware: `run.py` stops the app (Ctrl-C) and restarts the device after the tests. The instructions,
with a countdown, appear **on the Cardputer's screen**. `M5.begin()` already loads the BMI270's configuration;
Squirrel! only switches its power off - the test switches it on, measures and switches it off again.

| Test | What you do |
|---|---|
| `t01_identify` | - (chip id 0x24, configuration loaded, its type in `M5.Imu`, power state) |
| `t02_still` | lay it flat, screen up (registers compared with `M5.Imu.getAccel`) |
| `t03_orientation` | 1) screen up, 2) screen down, 3) upright, screen towards you, keyboard at the bottom, 4) on its left side |
| `t04_shake` | shake for 5 s |
| `t05_off` | - (off, as the app leaves it) |

The result of `t03` (which axis, with which sign, points "screen down") is the data for a future "face down = silent"
on both devices.

---

## Results: T-Watch 2020 V3, 2026-10-10 (MicroPython 1.25.0 ESP32_GENERIC SPIRAM)

Chip ESP32-D0WDQ6-V3, 16 MB flash (Winbond), PSRAM works (~4 MB of heap). It came with CircuitPython 10.2.1 - a full
copy of the flash and the project's files are in `.build/hwtest/` (the copy verified; only the NVS partition, which
CircuitPython writes at start-up, differed).

| Part | Result | What it means for the port |
|---|---|---|
| pins | as in CircuitPython's board definition and LilyGo's library | + `TOUCH_RST` = GPIO14 (a reset pulse before using touch) |
| AXP202 | id 0x41, battery 4.19 V / 100 %, ADC readings | |
| ST7789 display | **PASS** with MADCTL 0xC0, an 80-row offset, inversion | SPI **26.67 MHz, `miso=None`** - at 40 MHz MicroPython 1.25 crashes (a panic, not an exception), because MOSI = GPIO19 goes through the GPIO matrix; a whole screen in 78 ms |
| backlight | **PASS**, GPIO15 (PWM), powered by LDO2 at 3.3 V | |
| FT6336U touch | **PASS** 7/7 (corners, centre, 2 taps, a hold) | the coordinates match the picture (no transform) |
| vibration | **PASS**, GPIO4 | |
| side button | **PASS** (AXP202, the power key) | the AXP reports short / long presses itself (0x4A bits 1/0) and edges (0x4C bits 5/6); clear the pending interrupts (0x48-0x4C) first, or the INT line (GPIO35) stays low |
| MAX98357A speaker | **PASS** | powered by **LDO4 = 3.3 V** (it was 1.8 V!), as in LilyGo's library; LDO3 is unused on the V3; I2S **stereo** (BCK 26, WS 25, DOUT 33) |
| PCF8563 clock | runs, but **the VL bit** is set (time invalid, 2026-09-30) | the port has to write the time when it is first set and clear VL |
| BMA423 accelerometer | **PASS** without the configuration file (noise ~0.001 g) | face up −z, face down +z, "12" up −x, button up −y; "face down" = z > ~+0.8 g |
| PDM microphone | SKIP - `machine.I2S` has no PDM | a C module (later) |
