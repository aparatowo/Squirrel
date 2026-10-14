# Backlog

*[Polski](../pl/backlog.md) · [Français](../fr/backlog.md) · [Deutsch](../de/backlog.md)*

What is known to be wrong, what is not built yet, and what was planned and then done another way. State of version
2.0. Users meet the first part as the known limitations of the [release notes](../../releases/README.md).

## Known issues

### A. Link encryption is switched off

The Bluetooth records go over the air unencrypted; only pairing with a code in the app protects them from being
changed (see [bluetooth.md](bluetooth.md) §6). LE Secure Connections is in the code (`nuts.BLE_LINK_PAIRING = False`,
`ble/secrets.py`, `firmware_patches/0001-nimble-central-passkey.patch`) and worked on the devices, but the Cardputer
reset during some sessions.

The resets turned out to be another bug (2026-10-13): the boss's IRQ handler queued `tuple(data)`, and in MicroPython
`tuple()` of a tuple returns **the same object** - the IRQ's tuple on the NimBLE task's stack, overwritten by the radio
before `tick()` read it. Fixed (`tuple(list(data))`); 55 syncs without a reset since. With link encryption after the
fix: 5 of 5 syncs, then a freeze in the 6th (no panic, USB stopped taking data).

Next: a series with `tools/hwtest/ble_e2e.py --link`, explain the freeze, then `BLE_LINK_PAIRING = True` (the pairing in
the app stays, as the proof that this is your boss; encryption closes sniffing and offline guessing of the code). Check
at the same time whether `radio_gc` (no automatic garbage collection during a session) is still needed.

### B. A rare Cardputer freeze

About once in 70 syncs (2026-10-13): `mp_task` waited in `spi_flash_disable_interrupts_caches_and_other_cpu` (an
ordinary flash read) for core 0, which was serving interrupts but not tasks. The cause is not known; the Bluetooth
controller runs on core 0.

Mitigation: the main loop's watchdog (`nuts.WATCHDOG_S`, 60 s) restarts the device; data is kept. The firmware then
records what core 0 was doing (`firmware_patches/0002-panic-record.patch`); next time, read it with
`tools/hwtest/panic_record.py` and look for the cause.

### C. "no answer" right after connecting

Sometimes the boss gets no answer to the service discovery (7 of 30 in one series, 0 of 25 in the next). The message
says which events it waited for. Mitigation: the second round of a sync retries the devices that failed.

### D. The Cardputer's screenshots use the watch's font

`tools/sim/render_shots.py` draws text with the 6 × 8 font of `drivers/glcdfont.py` (+ `glcdfont_latin.py`), while a
Cardputer with a language other than English uses `squirrel.vlw`. The pictures in the guides are right in layout and
words, a little different in the shapes of the letters. Fix: render `.vlw` glyphs in `render_shots.py` (`vlw.py` can
read them).

### E. A node keeps one pairing key

`ble/peripheral.py` keeps one key per node (`"head"` in `ble_auth.json`): pairing the web page with the watch replaces
the Cardputer's key, and the Cardputer asks for a new code at its next sync (and the other way round). Documented for
users; a fix would keep a few keys and accept the proof of any of them - no change on the air or in the page.

## Not built yet

- **Edits on a node** (a phone connected to the watch): kept as proposals with the version they were made on; the boss
  decides at the next sync. A `SYNC_MODE` of *auto* / *ask* with a screen of differences (send / take / skip per
  category). Set `0x0B` is reserved ([bluetooth.md](bluetooth.md) §10).
- **A new boss**: taking over a full copy of the records from any node, with ids and counters, and pairing the nodes
  again.
- **The Web Bluetooth page** (`Squirrel!/tools/web/`): its codec is tested against `protocol.py` on the PC; with the watch
  (Chrome, the page opened from disk) connecting, pairing and reading work (`tools/hwtest/web_e2e.py`); editing from the
  page is not yet tried. Publishing it on GitHub Pages for phones: `.github/workflows/web-page.yml`, ready, not switched
  on.
- **The generic ESP32-S3 watch** (`ports/generic_s3_watch`): builds, not yet tried on a watch.
- **The watch's sound and microphone, the accelerometer** (still only switched off at start-up).
- **Ideas from the roadmap:**
  - the *Today* filter on the To-Do list;
  - emotion tags on an entry (🔥 urgent, 💡 idea, 😰 stress, 🕑 someday);
  - a single-task focus view (*What I'm doing now*: one To-Do, large);
  - automatic timestamps on notes;
  - back to the last opened note after a restart;
  - USB drive mode (the SD card seen from a computer);
  - an ultra power-saving mode.

## Done another way

| Planned | How it is done |
|---|---|
| Quick Capture (FN+SPACE from the clock) | the TAB menu on the clock: **TAB, M** - Mind dump, **TAB, T / N** - a To-Do / a note; **G0** records a voice note at once |
| A micro web server on the watch, for routines from a phone | the Web Bluetooth page: no Wi-Fi server, it talks to the devices directly |
| A port to programmable smartwatches | the T-Watch 2020 V3 port (2.0), the experimental generic ESP32-S3 port |
| Cooperation with the Cardputer | the Bluetooth sync (2.0) |
