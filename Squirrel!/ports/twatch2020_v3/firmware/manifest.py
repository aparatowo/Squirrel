# The firmware of the T-Watch port: MicroPython's usual ESP32 modules, plus Squirrel! frozen.
# build_firmware.py copies this folder next to the staged sources (squirrel/) before `make`.
include("$(PORT_DIR)/boards/manifest.py")
freeze("$(BOARD_DIR)/squirrel")
