# LilyGo T-Watch 2020 V3 - a MicroPython board definition kept in the Squirrel! repository (built with BOARD_DIR=,
# nothing in the MicroPython tree is changed).  ESP32-D0WDQ6-V3, 16 MB flash, 8 MB PSRAM (tested 2026-10-10).
set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.ble
    boards/sdkconfig.spiram
    ${MICROPY_BOARD_DIR}/sdkconfig.board
)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
