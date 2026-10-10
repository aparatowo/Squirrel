# pin_pulser.py - a GPIO switched on and off: a buzzer behind a transistor, a vibration motor
#
# The pin is LOW (= off) from the moment the object exists.  pwm_freq 0 = plain on / off (an active buzzer, a motor);
# otherwise the pin is driven with PWM at that frequency while on (a passive buzzer needs a tone).
# The constructor raises when the pin cannot be used.


class PinPulser:
    def __init__(self, pin_no, pwm_freq=0):
        from machine import Pin
        self.pin_no = pin_no
        self._pwm = None
        self._pin = Pin(pin_no, Pin.OUT, value=0)
        self._pin.value(0)
        if pwm_freq:
            from machine import PWM
            self._pwm = PWM(self._pin, freq=pwm_freq, duty_u16=0)

    @property
    def pwm(self):
        return self._pwm is not None

    def set(self, on):
        if self._pwm is not None:
            self._pwm.duty_u16(32768 if on else 0)
        else:
            self._pin.value(1 if on else 0)
