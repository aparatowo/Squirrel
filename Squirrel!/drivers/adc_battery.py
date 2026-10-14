# adc_battery.py - the battery measured on an ADC pin through a divider (no power-management chip)
#
# level() -> 0..100 from the voltage (a Li-ion curve), millivolts(), charging() -> None (nothing reports it on such a
# board; a pin that shows charging can be given).  The interface hw/battery.BatteryMonitor reads (power_source()).
_CURVE = ((4150, 100), (4050, 90), (3950, 78), (3850, 62), (3780, 50), (3720, 38), (3670, 25), (3620, 14),
          (3550, 6), (3450, 2), (3300, 0))           # mV -> % under a light load, between the points: a straight line


class AdcBattery:
    def __init__(self, pin, divider=2.0, charge_pin=None, charge_level=0, samples=8):
        """pin: the ADC GPIO; divider: battery voltage / pin voltage (2.0 for two equal resistors); charge_pin: a GPIO
        that reads `charge_level` while charging, or None."""
        from machine import ADC, Pin
        self._adc = ADC(Pin(pin), atten=ADC.ATTN_11DB)
        self._divider = divider
        self._samples = samples
        self._charge = Pin(charge_pin, Pin.IN) if charge_pin is not None else None
        self._charge_level = charge_level

    def millivolts(self):
        try:
            uv = sum(self._adc.read_uv() for _ in range(self._samples)) // self._samples
        except (OSError, AttributeError):
            return None
        return int(uv * self._divider / 1000)

    def level(self):
        mv = self.millivolts()
        if mv is None:
            return None
        if mv >= _CURVE[0][0]:
            return 100
        for (hi_mv, hi), (lo_mv, lo) in zip(_CURVE, _CURVE[1:]):
            if mv >= lo_mv:
                return lo + (hi - lo) * (mv - lo_mv) // (hi_mv - lo_mv)
        return 0

    def charging(self):
        if self._charge is None:
            return None
        return self._charge.value() == self._charge_level
