# bmi270.py - the BMI270 motion sensor (accelerometer + gyroscope) - so far only switched off
#
# The Cardputer ADV has one on the keyboard's I2C bus.  The app does not use it yet, and it draws current when left
# on, so it is switched off at start-up.  (Motion features - waking up when picked up, face down = silent - need the
# sensor's ~8 KB configuration file to be loaded first; see PORTING_PL.md.)

_PWR_CTRL = 0x7D                # bits: aux, gyr, acc, temp enable - 0 = all off


def off(i2c, addrs):
    """Switch the sensors off.  Returns the address that answered, or None."""
    if i2c is None:
        return None
    for addr in addrs:
        try:
            i2c.writeto_mem(addr, _PWR_CTRL, b"\x00")
            return addr
        except Exception:
            continue
    return None
