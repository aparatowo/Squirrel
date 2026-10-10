# features.py - which of the hardware-dependent features this firmware has (features.toml, port_config.FEATURES)
#
#   from features import has
#   if has("voice_notes"): ...
# A feature the port cannot do is not built: its modules are not in the firmware and the menus do not show it.

from port_config import FEATURES


def has(name):
    return name in FEATURES
