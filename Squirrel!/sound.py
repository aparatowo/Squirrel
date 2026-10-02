# sound.py - short signals as PCM, for Speaker.playRaw
#
# A pattern is a tuple of (frequency in Hz, duration in ms); frequency 0 is a pause.
# Loaded on demand by AudioManager.beep(), so it costs no memory until the first signal.

import math
import struct

RATE = 8000

PATTERNS = {
    "notify": ((880, 120), (0, 50), (1175, 200)),     # two rising notes
    "short": ((1000, 80),),
    "tick": ((1500, 12),),                             # metronome, quarter-hour tick
    "tock": ((1000, 12),),
    "cuckoo": ((1319, 170), (0, 70), (1047, 230)),     # on the hour
    "step": ((1000, 80), (0, 40), (1000, 80)),         # next block, light
    "go": ((1200, 90), (0, 40), (1500, 160)),          # hard block
    "rest": ((600, 150), (0, 40), (500, 220)),         # break
}


def build(pattern, rate=RATE, amplitude=12000):
    """PCM16 mono bytes for `pattern` (a name from PATTERNS, or a tuple of segments)."""
    segments = PATTERNS[pattern] if isinstance(pattern, str) else pattern
    total = 0
    for _freq, ms in segments:
        total += ms * rate // 1000
    buf = bytearray(total * 2)
    pos = 0
    for freq, ms in segments:
        n = ms * rate // 1000
        if freq:
            step = 2 * math.pi * freq / rate
            ramp = min(40, n // 4)                      # short fade in / out: no clicks
            for i in range(n):
                level = amplitude
                if ramp:
                    if i < ramp:
                        level = amplitude * i // ramp
                    elif i >= n - ramp:
                        level = amplitude * (n - 1 - i) // ramp
                struct.pack_into("<h", buf, (pos + i) * 2, int(level * math.sin(i * step)))
        pos += n
    return bytes(buf)
