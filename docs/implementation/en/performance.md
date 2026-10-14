# Memory, speed and energy

*[Polski](../pl/performance.md) · [Français](../fr/performance.md) · [Deutsch](../de/performance.md)*

Squirrel! has to fit the weakest of its devices: an ESP32-S3 **without PSRAM** (the Cardputer ADV, many cheap
watches) gives MicroPython about **160 KB** of heap for everything. What it costs today, and how it is kept small.

## 1. Measured (2.0)

| What | Value |
|---|---|
| The app's heap on the Cardputer (no PSRAM), on the clock | 54 KB of 160 KB |
| of that, the settings (95 of them) | 7.4 KB |
| A language other than English | under 1 KB of RAM (the tables stay in flash) |
| Looking up a text on the watch (ESP32 at 80 MHz) | 91 µs (763 µs without the cache); drawing a screen about 2 % slower than in English |
| The watch's display, whole frame buffer / strips | menu 132 / 141 ms, clock 292 / 366 ms |
| Frame buffer for 240 × 240 / 240 × 280, in strips | 115 / 134 KB, 19 KB |
| An automatic Bluetooth sync, on the watch | about 1 mAh (its battery: about 380 mAh) |

## 2. How it is kept small

- **Frozen code.** All modules are bytecode in flash (`build_firmware.py`): nothing is compiled on the device, and
  code takes no heap. Constant tables (translations, glyphs, the font) stay in flash too.
- **Settings as rows.** `appconfig` keeps one reference to each `SETTINGS` row of `appconfig_schema.py` instead of a
  copy per setting, and takes the defaults straight from `nuts`.
- **Translations** are one sorted tuple per language, searched by halves; a cache of the last 200 texts, and the
  user's own texts (`lang_<code>.tsv`) are the only ones in RAM. See [i18n.md](i18n.md).
- **The display in strips** without PSRAM (`drivers/st7789_fb.py`): the drawing calls of a frame are kept and replayed
  into a 40-row buffer, one band at a time. Chosen by itself: the whole frame only when it takes at most a quarter of
  the free heap; `[display] buffer_rows` forces strips. See [ports.md](ports.md).
- **Screens unloaded** (`POWER_UNLOAD_SCREENS`): a rarely used screen's objects go when you leave it.
- **Lazy imports** of what only one screen or one feature needs; a feature the device lacks is not in its firmware at
  all (`features.toml`).
- **Bluetooth:** only during a session; one record in memory at a time (sent and taken in parts); the automatic
  garbage collection is off during a session and `tick()` collects from the main loop - a collection started by an
  allocation inside the radio's IRQ ran on its small stack.

## 3. Energy

- The radios are on only while they work: Wi-Fi for the time at start-up, Bluetooth for a sync session (an ESP32
  cannot light-sleep with the BT controller on).
- The screen dims after a while without input; `POWER_SAVE` slows the CPU while it is dimmed.
- `POWER_SLEEP`: `light` (experimental) sleeps while dimmed and wakes on a key, button or touch; `deep` (the watch) sleeps deeply and
  wakes by its clock's alarm for the next routine, cuckoo or sync slot (`alarms.py` keeps the queue,
  `deep_sleep.py` saves and restores the state). After a wake the clock face is drawn before the rest of the app
  starts (`EARLY_CLOCK`).
- Automatic sync slots are on the clock, so the devices meet without talking first: the watch listens for 90 s per
  slot, the boss connects 20 s into it.

## 4. Safety nets

- **Watchdog** (`WATCHDOG_S`, 60 s): if the main loop does not come round, the device restarts; data is kept.
- **Panic record** (`firmware_patches/0002-panic-record.patch`): the reason and backtrace of a crash, or what core 0
  was doing when the task watchdog fired, survive the reset in RTC memory; `tools/hwtest/panic_record.py` reads them.
- `LOW_HEAP` in `hw/power.py`: a collection before the heap runs short.

## 5. Checking it again

```python
import gc, micropython; gc.collect(); micropython.mem_info()      # in the REPL of a running app (DEV mode)
```

`tools/hwtest/ble_e2e.py --mem` prints the Cardputer's memory every half second during a sync;
`tools/hwtest/twatch_gfx_bench.py` times the watch's drawing.
