# hw - the modules that talk to the hardware directly
#
#   audio_manager     speaker and microphone (recording, playback, short signals)
#   battery           battery level and charging, the battery log
#   buttons           buttons wired straight to GPIOs (G0)
#   buzzer            the extra buzzer on a GPIO, through an NPN transistor
#   cardputer_keypad  the keyboard (TCA8418 on I2C)
#   led               the built-in RGB LED
#   power             CPU frequency, light sleep, the motion sensor, garbage collection
#   radio             Wi-Fi and Bluetooth power
#   rtc_base, rtc_ds1302, rtc_provider    the clock: the internal one and an optional DS1302
#   sd_card           the SD card
#
# Everything else (settings, screens, logic) uses them through  from hw.<module> import ...
