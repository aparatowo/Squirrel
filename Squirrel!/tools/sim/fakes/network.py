# network.py - Wi-Fi that is always off and never connects
STA_IF, AP_IF = 0, 1
STAT_IDLE, STAT_CONNECTING, STAT_GOT_IP = 1000, 1001, 1010


class WLAN:
    def __init__(self, i=0):
        self._on = False

    def active(self, v=None):
        if v is None:
            return self._on
        self._on = bool(v)

    def isconnected(self):
        return False

    def connect(self, *a, **k):
        pass

    def disconnect(self):
        pass

    def status(self, *a):
        return STAT_IDLE

    def scan(self):
        return []

    def config(self, *a, **k):
        return ""

    def ifconfig(self, *a):
        return ("0.0.0.0",) * 4
