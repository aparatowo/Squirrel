# Third-party material

Squirrel! itself is under the MIT licence (see `LICENSE.txt`). The following is not Squirrel!'s own code.

## Font: `fonts/squirrel.vlw`
A 10-pixel bitmap rendering of **DejaVu Sans Mono** (Bitstream Vera glyphs, DejaVu changes in the public domain). Its licence requires
its notice to travel with every copy of the font: `fonts/LICENSE-DejaVu.txt`. Keep that file next to `squirrel.vlw` wherever the font goes
(a release archive, a copy on the SD card, a firmware image's file system). The font may not be sold by itself.

## Tools that make the font (not distributed with the app)
`tools/make_vlw.py` uses Pillow (HPND licence) and, if present, fontTools (MIT). They are installed by the user and not included in this repository.

## Firmware that the app runs on (not included in this repository)
Squirrel! runs on MicroPython / UIFlow2 firmware for the M5Stack Cardputer-ADV. `build_firmware.py` builds that firmware from the
user's own checkout of a firmware repository. That firmware is **not** Squirrel!'s code and has its own licences: MicroPython (MIT),
M5Stack UIFlow2 and the Cardputer-ADV fork (MIT), ESP-IDF (Apache-2.0), TinyUSB (MIT) and other components, among them Espressif
libraries and models from ESP-ADF / ESP-SR that come under Espressif's own terms. I have not checked every component.

**Before you publish a built `.bin`**, check the licences of everything that went into it and include their notices. The safer way is to
publish the source of Squirrel! and `build_firmware.py` and let people build their own image; the `dist/` folder is not meant for a repository.
