# bma423.py - the BMA423 accelerometer (T-Watch 2020) - so far only switched off
#
# The plain accelerometer works without the chip's configuration file (measured: noise ~0.001 g; face up -z, face
# down +z, 12 o'clock up -x, side button up -y); step counting and wrist gestures need that ~6 KB file loaded first.


def off(i2c, addrs):
    """Switch the accelerometer off.  Returns the address that answered, or None."""
    if i2c is None:
        return None
    for addr in addrs:
        try:
            i2c.writeto_mem(addr, 0x7D, b"\x00")      # PWR_CTRL: accelerometer off
            i2c.writeto_mem(addr, 0x7C, b"\x03")      # PWR_CONF: advanced power save (the chip's default)
            return addr
        except Exception:
            continue
    return None
