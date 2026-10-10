host = "pool.ntp.org"


def time():
    raise OSError("no network in the simulator")


def settime():
    raise OSError("no network in the simulator")
