# Testing

*[Polski](../pl/testing.md) · [Français](../fr/testing.md) · [Deutsch](../de/testing.md)*

Three levels: tests on the PC (no device), the whole app in a simulator (no device), and scripts that run on the
devices over USB. Run everything from `Squirrel!/`.

## 1. Tests on the PC

```bash
for t in tools/tests/test_*.py; do python3 "$t" || echo "FAILED: $t"; done
python3 -m unittest tools/tests/test_i18n.py         # (any of them also runs this way)
```

| Test | What it covers |
|---|---|
| `test_ble_protocol.py`, `test_ble_merge.py` | the Bluetooth record codecs, frames and who-is-right rules |
| `test_ble_node.py`, `test_ble_head.py` | a whole boss ↔ node sync over the fake radio (`tools/sim/fakes/bluetooth.py` links two radios "over the air"), pairing included |
| `test_ble_auto.py` | automatic sync: slots on the clock, the node as an alarm source, skipping a busy radio |
| `test_web_protocol.py` | the Web Bluetooth page's JavaScript codec gives the same bytes as `ble/protocol.py` (needs `node`) |
| `test_checklist.py`, `test_routines.py` | checklists (`>` lines, ticks kept apart), routines and their days |
| `test_cardputer_hw.py`, `test_hourglass_bars.py`, `test_battery.py`, `test_focus_wins.py` | the first Cardputer's key matrix and the DS3231 against fakes; the hourglass and the clock's time bars; `test_battery.py`: charging guessed from the voltage, the low-battery warnings, the LED's glow; `test_focus_wins.py`: focus time taken back, the success journal, the watch's double / triple tap |
| `test_appconfig.py` | `config.txt`: reading, writing, comments, defaults changed by a newer version |
| `test_i18n.py` | lookup, fallback to English, templates (`fill`), the user's own `lang_<code>.tsv` |
| `test_st7789_strips.py` | the display drawn in strips gives the same picture as the full frame buffer (MicroPython only: `framebuf`, viper - skipped under CPython) |

Plus `python3 tools/i18n/check.py` (every text translated, placeholders the same, labels short enough) and
`python3 build_firmware.py --stage-only --port <port>` for each port (imports, compilation).

## 2. The simulator

`tools/sim/` runs the whole app on the PC under the **MicroPython unix port** (the same MicroPython as the firmware),
with fakes of `M5`, `machine`, `esp32`, `network`, `bluetooth` ..., a clock that moves only when the code sleeps, and
the device's `/sd` and `/flash` in a folder. Building the unix port once: [tools/sim/README.md](../../../Squirrel!/tools/sim/README.md).

- **Comparing two versions:** a refactoring that does not change behaviour gives an identical trace - every display
  call, every log line, every file written:

  ```bash
  mkdir -p /tmp/base && git archive HEAD "Squirrel!" | tar -x -C /tmp/base
  tools/sim/compare.sh <micropython> "/tmp/base/Squirrel!" "$PWD" /tmp/simwork      # IDENTICAL / DIFFERENT
  ```

- **Every screen, deep** (after a change of the UI or a translation): `crawl_scenario.py` opens every menu entry, every
  screen with a few keys on it, every setting of Personalize, each list item and the notifications; with
  `SQUIRREL_SIM_TOUCH=1` the same app as on a 240 x 240 touch screen, every button tapped (render with `--height 240`).
  `check_trace.py` lists text off the screen and English left in another language:

  ```bash
  SQUIRREL_SIM_SCENARIO=tools/sim/crawl_scenario.py <micropython> -X heapsize=16M tools/sim/run_sim.py "$PWD" /tmp/c /tmp/c.txt
  python3 tools/sim/check_trace.py /tmp/c.txt --lang de                        # OFF / ENGLISH / ERROR findings
  python3 tools/sim/render_shots.py /tmp/c.txt /tmp/c-shots                    # the pictures, named by place
  ```

- **Screenshots of the Cardputer** for the guides: a scenario of 34 states, with sample content in the language of the
  work folder's `config.txt` (`LANGUAGE=pl` ...), turned into PNG files:

  ```bash
  mkdir -p /tmp/w/sd/Squirrel /tmp/w/flash/fonts && cp squirrel.vlw /tmp/w/flash/fonts/
  echo "LANGUAGE=pl" > /tmp/w/sd/Squirrel/config.txt
  SQUIRREL_SIM_SCENARIO=tools/sim/shots_scenario.py <micropython> -X heapsize=8M tools/sim/run_sim.py "$PWD" /tmp/w /tmp/trace.txt
  python3 tools/sim/render_shots.py /tmp/trace.txt ../shots/cardputer/pl
  ```

  The font in `/flash/fonts/` matters: without it the app shows accented letters plain. The pictures are drawn with
  the watches' 6 × 8 font, not the Cardputer's `.vlw` ([backlog](backlog.md) D).

## 3. On the devices

Close Thonny first (it holds the port). `ls /dev/serial/by-id/` names the ports.

| Tool | What it does |
|---|---|
| `tools/hwtest/run.py PORT SCRIPT [TEST ...]` | runs a hardware test script over the REPL and shows its results live: `RESULT\|test\|PASS / FAIL / INFO / ASK / SKIP\|details` (ASK: confirm what you saw, heard or felt); a log in `.build/hwtest/`. `PORT` may be `auto`. A script runs only on the device named in its first line (`# EXPECT_MACHINE: ...`) |
| `twatch_hw.py`, `twatch_accel.py`, `cardputer_accel.py`, `cardputer_hw.py` | the scripts: the watch's chips one by one (PMU, display, touch, clock, vibration), the accelerometers; `cardputer_hw.py`: the DS3231 on the Grove port (both Cardputers), the first Cardputer's keys and LED |
| `twatch_gfx_bench.py` | drawing speed of the watch's display driver |
| `tools/hwtest/twatch_phase0.sh PORT` | before the first flash of a watch: chip and flash id, a full 16 MB copy of the flash with its MD5 (restores the factory software) |
| `tools/hwtest/twatch_screens.py PORT --lang pl` | screenshots of the watch's screens read from its frame buffer into `shots/twatch/<lang>/` (it writes a sample checklist and deletes it again) |
| `tools/hwtest/ble_e2e.py WATCH CARDPUTER` | a Bluetooth sync end to end through both apps' screens; `--link` with link encryption, `--mem` memory every half second, `--head-files` the boss runs the PC's `ble/` package (as `.mpy`) instead of its frozen one |
| `tools/hwtest/panic_record.py PORT` | the reason and backtrace of the Cardputer's last panic or freeze, from RTC memory (its TinyUSB console shows nothing when it crashes) |
| `tools/ble_pc_head.py` | the PC as the boss, for testing a watch without a Cardputer (needs `bleak`) |

On a running device: `import sq_info; sq_info.report()` (the build, shadowing files, the font), and the start-up log
`/flash/boot_log.txt` (Cardputer) or `/boot_log.txt` (watch).

## 4. Before a release

1. The PC tests, `check.py`, `--stage-only` for every port.
2. `compare.sh` against the last release where behaviour should not have changed.
3. Build and flash both devices; `ble_e2e.py` a few times; a sync from each device's own screen.
4. Screenshots in every language (Cardputer from the simulator, the watch from the device), then **look at them as a
   user**: does every text fit, is it translated, does it sound like the rest?
