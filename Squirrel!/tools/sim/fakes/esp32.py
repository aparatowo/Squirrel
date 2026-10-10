# esp32.py - fake RMT / NVS
class RMT:
    def __init__(self, *a, **k):
        pass

    def write_pulses(self, *a):
        pass

    def wait_done(self, **k):
        return True

    def deinit(self):
        pass

    @staticmethod
    def bitstream_channel(*a):
        return 3


class NVS:
    def __init__(self, ns):
        self._d = {}

    def get_i32(self, k):
        raise OSError(-4354)

    def set_i32(self, k, v):
        self._d[k] = v

    def get_blob(self, k, buf):
        raise OSError(-4354)

    def set_blob(self, k, v):
        self._d[k] = v

    def commit(self):
        pass
