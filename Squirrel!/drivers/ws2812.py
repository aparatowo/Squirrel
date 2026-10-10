# ws2812.py - one WS2812 RGB LED on a GPIO (the Cardputer ADV's built-in LED, G21)
#
# Two ways to send a frame, tried in this order (see hw/led.py for why):
#   WS2812Rmt        one esp32.RMT channel set up ONCE, its line idle low;
#   WS2812Bitstream  machine.bitstream (what the neopixel modules do inside; this firmware has no `neopixel` module) -
#                    it installs an RMT driver for every frame and gives the pin back to plain GPIO afterwards, so the
#                    pin is explicitly held low between frames.
# Both: show(0xRRGGBB), release(), and a `name` shown by the LED tests.

_RMT_CHANNEL = 0                # machine.bitstream uses its own (esp32.RMT.bitstream_channel(), 3 here)


class WS2812Rmt:
    """One WS2812 on a GPIO, sent through an esp32.RMT channel that is configured once and stays on the pin."""
    name = "RMT"
    _ZERO = (4, 8)                               # 100 ns ticks: 400 ns high, 800 ns low
    _ONE = (8, 4)                                # 800 ns high, 400 ns low

    def __init__(self, pin_no):
        import esp32
        from machine import Pin
        Pin(pin_no, Pin.OUT, value=0)
        self._rmt = esp32.RMT(_RMT_CHANNEL, pin=Pin(pin_no), clock_div=8, idle_level=False)    # 80 MHz / 8 = 10 MHz

    def show(self, rgb):
        pulses = []
        for byte in (rgb >> 8 & 0xFF, rgb >> 16 & 0xFF, rgb & 0xFF):     # a WS2812 takes green, red, blue
            for bit in range(7, -1, -1):
                pulses.extend(self._ONE if byte >> bit & 1 else self._ZERO)
        self._rmt.wait_done(timeout=10)
        self._rmt.write_pulses(pulses, True)

    def release(self):
        try:
            self._rmt.deinit()
        except Exception:
            pass


class WS2812Bitstream:
    """One WS2812 on a GPIO, written with machine.bitstream (the neopixel modules do the same) - the fallback."""
    name = "bitstream"
    TIMING = (400, 850, 800, 450)                # ns: 0 high, 0 low, 1 high, 1 low (800 kHz)

    def __init__(self, pin_no):
        from machine import Pin, bitstream
        self._pin = Pin(pin_no, Pin.OUT, value=0)    # low between frames: bitstream gives the pin back to GPIO each time
        self._bitstream = bitstream
        self._buf = bytearray(3)

    def show(self, rgb):
        self._buf[0] = rgb >> 8 & 0xFF            # a WS2812 takes green, red, blue
        self._buf[1] = rgb >> 16 & 0xFF
        self._buf[2] = rgb & 0xFF
        self._bitstream(self._pin, 0, self.TIMING, self._buf)

    def release(self):
        pass


DRIVERS = (WS2812Rmt, WS2812Bitstream)
