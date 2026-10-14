// A generic ESP32-S3 smartwatch (see mpconfigboard.cmake)
#define MICROPY_HW_BOARD_NAME "ESP32-S3 smartwatch"
#define MICROPY_HW_MCU_NAME "ESP32S3"
// the console on the S3's own USB-Serial/JTAG (not TinyUSB): it survives resets, and a panic's output reaches it
#define MICROPY_HW_ENABLE_USBDEV (0)
#define MICROPY_HW_USB_CDC (0)
