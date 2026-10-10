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


def millivolts():
    try:
        from M5 import Power
        value = Power.getBatteryVoltage()
        return int(value) if isinstance(value, (int, float)) and value > 0 else None
    except Exception:
        return None
