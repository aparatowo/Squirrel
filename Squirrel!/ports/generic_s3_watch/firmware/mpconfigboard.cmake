# A generic ESP32-S3 smartwatch - a MicroPython board definition kept in the Squirrel! repository (built with
# BOARD_DIR=, nothing in the MicroPython tree is changed).  EXPERIMENTAL: see ../port.toml.
set(IDF_TARGET esp32s3)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.ble
    boards/sdkconfig.spiram_sx
    boards/sdkconfig.spiram_oct                 # octal PSRAM (N8R8 / N16R8 - the usual watch module); a quad one: drop this line
    boards/sdkconfig.240mhz
    ${MICROPY_BOARD_DIR}/sdkconfig.board
)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
