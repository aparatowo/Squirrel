# m5_power.py - battery level, charging and voltage through M5.Power (UIFlow 2 firmware)
#
# Every function returns None when the value cannot be read.


def level():
    try:
        from M5 import Power
        return Power.getBatteryLevel()
    except Exception:
        return None


_PMIC_UNKNOWN, _PMIC_ADC = 0, 1      # M5 Power.getType(): no power chip that reports charging


def charging():
    """True / False, or None when the device cannot tell.

    M5Unified answers "charge unknown" on boards without a charger chip it can read - the Cardputer ADV is one (its
    battery is only measured through the ADC) - and the MicroPython binding turns that into True.  Taken at face value
    the device would always be "charging", so on such boards the answer is None (unknown) instead."""
    try:
        from M5 import Power
        if Power.getType() in (_PMIC_UNKNOWN, _PMIC_ADC):
            return None
        return bool(Power.isCharging())
    except Exception:
        return None


_USB_DSTS = 0x60080808               # ESP32-S3 USB OTG core (TinyUSB's): DSTS - bit 0 suspended, bits 8..21 the frame
                                    # number (esp-idf soc/esp32s3 usb_dwc_struct.h)


def usb_host():
    """True when a USB host (a computer) is sending frames - it powers the Cardputer; False when the bus is idle (a
    charger without data, or nothing: the ESP32-S3 cannot tell those apart); None when it cannot be read."""
    try:
        import time
        from machine import mem32
        a = mem32[_USB_DSTS]
        time.sleep_ms(2)                         # a frame every millisecond at full speed
        b = mem32[_USB_DSTS]
        if b & 1:
            return False                         # suspended: no frames
        return (a >> 8 & 0x3FFF) != (b >> 8 & 0x3FFF)
    except Exception:
        return None


def millivolts():
    try:
        from M5 import Power
        value = Power.getBatteryVoltage()
        return int(value) if isinstance(value, (int, float)) and value > 0 else None
    except Exception:
        return None
