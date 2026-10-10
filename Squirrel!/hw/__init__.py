# hw - the parts of the app that run the hardware, whatever device it is
#
#   audio_manager     recording, playback, short signals (through the port's Mic / Speaker objects)
#   battery           battery level and charging (from the port's power source), the battery log
#   buzzer            a buzzer on a GPIO: modes, which features may use it, quiet hours
#   led               an RGB LED: modes, colours, the breathing and charging lights, quiet hours
#   ports             what a port has to provide (documentation: board, display, input, buttons, storage ...)
#   power             CPU frequency, light sleep, garbage collection
#   radio             Wi-Fi and Bluetooth power
#   rtc_base, rtc_provider    the clock: the internal one, and the port's hardware clock if it has one
#   touch_input       a touch screen as the input: gestures -> actions, where the finger is (any touch chip)
#
# The chip drivers are in drivers/, put together per device by ports/<port>/board.py.
# Everything else (settings, screens, logic) uses these through  from hw.<module> import ...
