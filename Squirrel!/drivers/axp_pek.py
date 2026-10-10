# axp_pek.py - the AXP202's power key as a button (the T-Watch 2020's side button)
#
# The chip itself tells a short press from a long one (IRQ status 3: 0x4A bits 1 / 0); pressed() reports each short
# press once.  Held for longer than its shutdown time (6 s on the watch) the key switches the watch off - by hardware.


class PekButton:
    held_at_start = False

    def __init__(self, axp, long=False):
        self._axp = axp
        self._long = long                       # True: this button reports long presses instead of short ones

    def pressed(self):
        try:
            return self._axp.long_press() if self._long else self._axp.short_press()
        except OSError:
            return False
