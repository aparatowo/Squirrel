# Building the firmware

*[Polski](../pl/building.md) · [Français](../fr/building.md) · [Deutsch](../de/building.md)*

`Squirrel!/build_firmware.py` builds a firmware image with the whole app **frozen** into it: the code is bytecode in
flash, not files on the device and not compiled into RAM at start-up. It needs only the Python standard library. The
short version for users is in [guides/en/getting-started.md](../../guides/en/getting-started.md); this is the whole
story. Devices and their `port.toml`: [ports.md](ports.md).

Run every command inside `Squirrel!/`.

## 1. Once per computer

```bash
python3 build_firmware.py --install-idf          # ESP-IDF 5.4.2 (~1 GB) into ~/esp-idf-v5.4.2 (or: --install-idf DIR)
python3 build_firmware.py --check                # what is in place, what is missing - changes nothing
```

- **ESP-IDF 5.4.x only.** The Cardputer's firmware is patched for 5.4.2; with 5.5 its microphone records silence,
  older ones do not build it. The script finds 5.4.x by itself even when `IDF_PATH` in your shell points elsewhere.
- **Cardputer, once:** `sudo apt install quilt`, then `python3 build_firmware.py --setup` (submodules, patches,
  littlefs, mpy-cross of the UIFlow repository; marker `.build/setup.done`, `--force` repeats it).
- **The watches** need nothing more: the first build clones MicroPython v1.25.0 into `vendor/micropython` and applies
  the port's patches itself.

The firmware repository of the Cardputer (`cardputer-adv-micropython`) is cloned into `vendor/` on the first run.
Another location: `--repo`, the `SQUIRREL_FW_REPO` variable or `build_config.json`:

```json
{"repo": "/path/to/cardputer-adv-micropython", "idf": "/path/to/esp-idf-v5.4.2", "port": "twatch2020_v3", "exclude": []}
```

## 2. Every day

```bash
python3 build_firmware.py --stage-only                    # seconds: collect the sources, check imports, compile them
python3 build_firmware.py                                 # full image -> dist/squirrel-<board>-<git>-<time>.bin (+ .txt)
python3 build_firmware.py --flash /dev/ttyACM0            # build and flash
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0     # another device
```

The `.txt` next to the image lists what is in it. The build runs in a clean environment (no `IDF_*` variables from
your shell) and starts over when the previous one used another ESP-IDF.

**What a build does:** it reads `ports/<port>/port.toml` and `features.toml`, writes `port_config.py` for that device,
leaves out the modules of features the device lacks, the drivers its `port.toml` does not name and the folders of other
ports, stops if any module imports something that is not in this build, compiles everything with the firmware's own
`mpy-cross`, and freezes it into a board definition of its own (the firmware repository's files are not changed: a
derived board, listed in `.git/info/exclude`; `--clean` removes it). `lang/<code>.py` (the translations, built from
`translations/*.tsv` by `tools/i18n/build.py`) is frozen like any module, and the Cardputer's font goes into the
image's system partition.

## 3. Flashing

```bash
python3 build_firmware.py --flash-image <file from dist/> --flash /dev/ttyACM0    # an image built earlier
python3 build_firmware.py --setup-device /dev/ttyACM0                            # only prepare a device
python3 build_firmware.py --flash /dev/ttyACM0 --no-device-setup                 # flash, do not prepare
```

- Close Thonny (or anything holding the port). `ls /dev/serial/by-id/` names the devices: `...Espressif...` /
  `...M5Stack...` is the Cardputer, `...1a86...` the T-Watch (CH9102).
- **Cardputer:** its USB console is TinyUSB, part of the app, and a reset drops the connection - flashing a running
  Cardputer often fails. Hold **G0** while plugging the cable in: it waits in download mode (black screen, the port is
  then called `...Espressif_USB_JTAG...`). After flashing it starts by itself and comes back under its app name; the
  message "did not come back" then only means the name changed.
- The Cardputer's image is the whole flash from 0x0 (UIFlow's NVS settings are replaced; your data is on the SD card);
  the watches' images do not touch the data partition (`/Squirrel` stays).

**Preparing the device** (done after `--flash PORT` by itself, each step only when needed, and only on a device whose
`sys.implementation._machine` contains the port's `[port] machine`):

1. `/flash/main.py` (or `/main.py`) = `device/main.py`, which starts Squirrel!; an older one is kept as `main.py.old`;
2. Cardputer: UIFlow's `/flash/boot.py` is renamed to `boot.py.uiflow` when it imports `startup`, which this firmware
   lacks (renaming it back brings the UIFlow menu back);
3. Cardputer: UIFlow's boot option `boot_option = 0` (run `main.py` at once).

## 4. Checking a device

```python
import sq_info; sq_info.report()       # in Thonny
```

It shows the build, the number of frozen modules, files that **shadow** frozen modules, whether `main.py` starts the
app, the font, and where `nuts` came from. The start-up log (`/flash/boot_log.txt` on the Cardputer, `/boot_log.txt` on
the watch) has a line `[MAIN] frozen build <id> (N modules)`.

Do not leave `.py` / `.mpy` modules on the device's flash (besides `main.py`): they would shadow the frozen ones of the
same name.

## 5. DEV mode: code changes without a new firmware

Create an empty file `/flash/DEV` (the watch: `/DEV`) and put the changed `.py` files in `/flash/apps/Squirrel/`
(subfolders as in the sources). They now win over the frozen ones; delete `DEV` to go back. A folder (`screens/`,
`hw/`, `drivers/`, `ports/`) on the device hides the **whole** frozen package of that name, so copy it whole. A `.mpy`
wins over a `.py` of the same name.

Quick help when a device runs out of memory compiling `.py` files: `--build-mpy-cross` then `--mpy` writes `.mpy`
files to `dist/mpy/` (no ESP-IDF needed).

## 6. Other options

| Option | What it does |
|---|---|
| `--target build` | the app only (`micropython.bin`) - not a complete image |
| `--target pack_all` | the image with an **empty** user file system: wipes `/flash` |
| `--gen-port-config` | writes `port_config.py` next to the sources (for DEV mode and the simulator); default port unless `--port` |
| `--exclude FILE` | leave a file out of the image (repeatable; PC scripts such as `vlw.py` are left out by themselves) |
| `--prefer newer\|flat\|screens` | the same screen in two places with different content: which one wins |
| `--update-repo` | `git pull` in the firmware repository |
| `--reset-deps` | delete `dependencies.lock` and `managed_components` (re-resolved on the next build) |
| `--diagnose` | explain the last failed build from `.build/make.log` |
| `--allow-any-idf` | build with another ESP-IDF (not for `--setup`; not recommended) |
| `--allow-missing` | build even if the base board's manifest names a missing file |

The `port_config.py` next to the sources belongs to the default port (the Cardputer); after `--gen-port-config --port
X`, restore it before committing. A build always writes its own.

## 7. Patches to the firmware

The firmware is changed only by patches kept in the repository, applied to a temporary copy as a stack:

| Patch | What it does |
|---|---|
| `firmware_patches/0001-nimble-central-passkey.patch` | NimBLE: the central's passkey events (link encryption, off for now) |
| `firmware_patches/0002-panic-record.patch` | a panic or task-watchdog report kept in RTC memory over the reset (`tools/hwtest/panic_record.py` reads it): the Cardputer's TinyUSB console shows nothing when it crashes |
| `ports/<port>/firmware/patches/*.patch` | per watch: what its MicroPython build needs |

## 8. When something goes wrong

| Message | What to do |
|---|---|
| `No ESP-IDF 5.4.x found` | `--install-idf` |
| `quilt is not installed` | `sudo apt install quilt` |
| `mpy-cross is not built` | `--setup` (the Cardputer's repository is not set up yet) |
| `Two different copies of the same screen module` | delete the stale file, or `--prefer newer` |
| `... does not compile with the firmware's mpy-cross` | that file uses syntax MicroPython does not have |
| `imports ..., which is not in the sources (of this port)` | a module needs a feature or driver this port leaves out: import it inside the function that needs it, or add it to the port |
| `CFG_TUD_CDC_EP_BUFSIZE undeclared` | mismatched TinyUSB components: pin `espressif/tinyusb` to `0.15.0~10` in `m5stack/main/idf_component.yml`, then `--reset-deps` |
| `Cannot stat .../firmware_info.py` | the script generates it for the base board before building; if that fails it says what to check (`--allow-missing` skips the check) |
| flashing fails | close Thonny; Cardputer: hold G0 while plugging in; Linux: `sudo usermod -aG dialout $USER` and log in again |
| no app after flashing | since 2.1 the firmware writes `/flash/main.py` itself on a first start (a complete image from M5Burner, an erased chip); otherwise `--setup-device PORT`; check `/flash/main.py` |
| anything else | the whole output is in `.build/make.log`; `--diagnose` recognises the known cases |
