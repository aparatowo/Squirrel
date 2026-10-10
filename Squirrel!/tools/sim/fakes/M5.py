# M5.py - a fake of the UIFlow 2 M5 module: every display call is written to sim_state.trace
import sim_state as _s


def _fmt(v):
    if isinstance(v, int) and not isinstance(v, bool) and v > 255:
        return "0x%06X" % v
    return repr(v)


class _Lcd:
    def __init__(self):
        self._size = 1
        self._bright = 80
        self.font = None

    def _rec(self, name, args):
        _s.trace.append("%s(%s)" % (name, ", ".join(_fmt(a) for a in args)))

    def setTextSize(self, *a):
        self._size = a[0]
        self._rec("setTextSize", a)

    def textWidth(self, text, *a):
        return len(text) * 6 * self._size

    def fontHeight(self, *a):
        return 8 * self._size

    def width(self):
        return 240

    def height(self):
        return 135

    def setBrightness(self, v):
        self._bright = v
        self._rec("setBrightness", (v,))

    def getBrightness(self):
        return self._bright

    def setFont(self, path):
        self.font = path
        self._rec("setFont", (path,))

    def setRotation(self, *a):
        self._rec("setRotation", a)

    def __getattr__(self, name):
        if name.startswith("COLOR_") or name.startswith("_"):
            raise AttributeError(name)

        def call(*a, **k):
            self._rec(name, a)
        return call


Lcd = _Lcd()
Display = Lcd


class _Stub:
    """Any call is accepted; a few return values the app looks at are given explicitly."""
    def __init__(self, name, values=None):
        self._name = name
        self._values = values or {}

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)
        value = self._values.get(attr)

        def call(*a, **k):
            return value(*a) if callable(value) else value
        return call


Power = _Stub("Power", {"getBatteryLevel": 77, "isCharging": True, "getType": 1, "getBatteryVoltage": 3900})
_vol = [70]
Speaker = _Stub("Speaker", {"begin": True, "isPlaying": False, "isEnabled": True, "getVolume": lambda: _vol[0],
                            "setVolume": lambda v: _vol.__setitem__(0, v), "isRunning": True, "tone": True,
                            "playRaw": True, "playWav": True})
Mic = _Stub("Mic", {"begin": True, "isRecording": False, "isEnabled": True, "record": True, "isRunning": True})
Led = _Stub("Led", {"getCount": 0})
BtnA = _Stub("BtnA", {"isPressed": False, "wasPressed": False})


def begin(*a, **k):
    _s.trace.append("M5.begin()")


def update():
    pass
