# drivers - one module per CHIP (or firmware API), not per device, so that the next port can reuse it
#
#   bmi270          the BMI270 motion sensor (only switched off so far)
#   ds1302          the DS1302 clock chip (3-wire bus)
#   gpio_button     a button wired straight to a GPIO
#   m5_audio        M5.Mic / M5.Speaker of the UIFlow 2 firmware
#   m5_display      M5.Lcd of the UIFlow 2 firmware
#   m5_power        M5.Power of the UIFlow 2 firmware (battery level, charging, voltage)
#   pin_pulser      a GPIO switched on and off (a buzzer through a transistor; a vibration motor)
#   sd_spi          an SD card on SPI (machine.SDCard, or the UIFlow helper)
#   tca8418_keypad  a key matrix scanned by a TCA8418 on I2C
#   ws2812          one WS2812 RGB LED
#
# A driver gets its pins and addresses as arguments: it never reads port_config.  Which drivers a device has, and how
# they are wired, is said by ports/<port>/port.toml and put together by ports/<port>/board.py.
