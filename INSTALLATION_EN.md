# 🐿️ Squirrel! — Installation Guide (EN)

---

## Before you start — what you need

### On your computer

| What? | Why? | How to check? |
|---|---|---|
| **Python 3.10+** | Builds the firmware and runs the script | In terminal: `python3 --version` |
| **Git** | Downloads the source code | In terminal: `git --version` |
| **Thonny** | Uploads files to the device | Open the Thonny app |
| **USB-C cable** | Connects Cardputer to your computer | Check physically |
| **microSD card** | Stores your notes | Must be inserted in the Cardputer |

> 💡 **Linux / macOS:** Python and Git are usually already installed.
> **Windows:** Download Python from [python.org](https://python.org) and Git from [git-scm.com](https://git-scm.com).

---

## Step 1 — Download Squirrel! code

Open a terminal and type these commands **one at a time**:

```bash
cd ~
```

```bash
git clone https://github.com/aparatowo/Squirrel.git
```

```bash
cd Squirrel
```

---

## Step 2 — Install required Python libraries

```bash
pip3 install esptool
```

That's the only external library needed to build and flash the firmware.

---

## Step 3 — Build the firmware

> ⚠️ This step can take **a few to several minutes**. That's normal — your computer is working.

```bash
cd apps
```

```bash
python3 build_firmware.py
```

The script will download everything it needs and build a `.bin` file with Squirrel!'s modules frozen inside.

When it finishes, you'll find a file called `squirrel_firmware.bin` (or similar — check what the script printed at the end) in the `apps/` folder.

---

## Step 4 — Flash the firmware to Cardputer

### 4a. Put the device into flash mode

1. Turn the Cardputer off.
2. Hold the **`G0`** key (small side button).
3. While holding `G0` — plug the USB-C cable into your computer.
4. Release `G0`. The screen will stay black — that's normal.

### 4b. Flash the file

```bash
python3 build_firmware.py --flash /dev/ttyACM0
```

> If the script asks for a port, type:
> - **Linux:** `/dev/ttyUSB0` or `/dev/ttyACM0`
> - **macOS:** `/dev/cu.usbserial-*` (check with: `ls /dev/cu.*`)
> - **Windows:** `COM3` (or another letter — check Device Manager)

Flashing takes about **1–2 minutes**.

### 4c. Restart

When done, unplug and replug the cable (or press the reset button on the device). The Cardputer will boot normally.

---

## Step 5 — Preparing the device (automatic)

Nothing has to be uploaded by hand. The whole app is **frozen** into the firmware, and `build_firmware.py --flash PORT`
prepares the device by itself after flashing:

1. writes `/flash/main.py` (from `Squirrel!/device/main.py`; 5 lines that start the app from the firmware);
2. renames UIFlow's `/flash/boot.py` to `/flash/boot.py.uiflow` when it cannot run with this firmware;
3. sets UIFlow's boot option to "run `main.py`".

If you flashed without naming the port (or earlier), do it separately (close Thonny - it holds the port):

```bash
python3 build_firmware.py --setup-device /dev/ttyACM0
```

> ⚠️ **Do not upload** the app's `.py` files to `/flash/apps/Squirrel/` or `/flash/` - they would hide the code frozen in the
> firmware.  The exception is DEV mode (see `Squirrel!/BUILD.md`).

---

## Step 6 — Prepare the microSD card

The card must be formatted as **FAT32**.

Squirrel! will create the `/Squirrel/` folder automatically on first launch.
You don't need to do anything manually.

---

## All done! 🎉

Restart the Cardputer - Squirrel! starts at once (no UIFlow2 menu).

---

## Something not working?

| Problem | What to do |
|---|---|
| Black screen after flashing | Check the USB-C cable, try a different port on your computer |
| Thonny can't see the device | Make sure the device is on and not in flash mode |
| `port not found` error | Check the port in Device Manager (Windows) or `ls /dev/tty*` (Linux/Mac) |
| App doesn't start | Run `python3 build_firmware.py --setup-device /dev/ttyACM0`; in Thonny: `import sq_info; sq_info.report()` |
| Notes not saving | Check that the microSD card is inserted and formatted as FAT32 |

---

*Squirrel! © Rafał Nitychoruk (Ijon Tichy) — MIT licence*
