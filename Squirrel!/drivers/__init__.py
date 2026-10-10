# drivers - one module per CHIP (or firmware API), not per device, so that the next port can reuse it
#
#   axp202          the AXP202 power chip: supplies, battery, the power key (T-Watch 2020)
#   axp_pek         the AXP202's power key as a button
#   bma423          the BMA423 accelerometer (only switched off so far)
#   bmi270          the BMI270 motion sensor (only switched off so far)
#   ds1302          the DS1302 clock chip (3-wire bus)
#   flash_storage   the app's folder on the internal flash (no SD card)
#   ft6336          the FT6336U touch controller: read_point() only (gestures: hw/touch_input.py)
#   glcdfont        the classic 5x7 font of Adafruit GFX (M5GFX's default font) - used by st7789_fb
#   gpio_button     a button wired straight to a GPIO
#   m5_audio        M5.Mic / M5.Speaker of the UIFlow 2 firmware
#   m5_display      M5.Lcd of the UIFlow 2 firmware
#   m5_power        M5.Power of the UIFlow 2 firmware (battery level, charging, voltage)
#   pcf8563         the PCF8563 clock chip
#   pin_pulser      a GPIO switched on and off (a buzzer through a transistor; a vibration motor)
#   sd_spi          an SD card on SPI (machine.SDCard, or the UIFlow helper)
#   st7789_fb       an ST7789 panel drawn through a frame buffer (framebuf + viper), only changes are sent
#   tca8418_keypad  a key matrix scanned by a TCA8418 on I2C
#   ws2812          one WS2812 RGB LED
#
# A driver gets its pins and addresses as arguments: it never reads port_config.  Which drivers a device has, and how
# they are wired, is said by ports/<port>/port.toml and put together by ports/<port>/board.py.
