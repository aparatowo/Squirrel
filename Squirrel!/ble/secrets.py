# ble/secrets.py - the keys NimBLE asks the application to keep (_IRQ_GET_SECRET / _IRQ_SET_SECRET): this device's
# identity key and the bonds made by pairing (docs/implementation/en/bluetooth.md 6)
#
# Answered from memory in the IRQ handler (the Bluetooth stack's task: no file system there); a key that changed is
# written to the file by flush(), from tick().  The file is on the internal flash, never on a removable card.
# An IRQ handler that answered "not stored" (None) to SET_SECRET made the Cardputer's firmware reset (2026-10-12).
import json

_IRQ_GET_SECRET = 29
_IRQ_SET_SECRET = 30


class Secrets:
    """Keys by type, then by key bytes: {sec_type: {key: value}}.  The IRQ path only looks things up and stores
    copies - no iterators, no new tuples (work in the stack's task reset the Cardputer before, 2026-10-12)."""

    def __init__(self):
        self._keys = {}
        self._lists = {}                 # sec_type -> [values], for the lookups by index (rebuilt outside the IRQ)
        self._path = None
        self._dirty = False

    def use(self, path):
        """Keep the keys in `path` (read now; written by flush())."""
        if path == self._path:
            return
        self._path = path
        try:
            with open(path) as f:
                for sec_type, key, value in json.loads(f.read()):
                    self._keys.setdefault(sec_type, {})[bytes.fromhex(key)] = bytes.fromhex(value)
        except (OSError, ValueError, TypeError):
            pass
        self._relist()

    def _relist(self):
        self._lists = {t: list(d.values()) for t, d in self._keys.items()}

    def flush(self):
        if not self._dirty:
            return
        self._dirty = False
        self._relist()
        if self._path is None:
            return
        try:
            with open(self._path, "w") as f:
                f.write(json.dumps([[t, k.hex(), v.hex()] for t, d in self._keys.items() for k, v in d.items()]))
        except OSError as e:
            print("[BLE] cannot save the keys: %s" % e)

    def forget(self):
        """Every bond goes (the device's own identity key too): pairing starts from scratch."""
        self._keys = {}
        self._dirty = True
        self.flush()

    def count(self):
        return sum(len(d) for d in self._keys.values())

    def handles(self, event):
        return event == _IRQ_GET_SECRET or event == _IRQ_SET_SECRET

    def irq(self, event, data):
        """Answer a GET_SECRET / SET_SECRET; called from the IRQ handler."""
        if event == _IRQ_SET_SECRET:
            sec_type, key, value = data
            d = self._keys.get(sec_type)
            if d is None:
                d = self._keys[sec_type] = {}
            if value is None:
                d.pop(bytes(key), None)
            else:
                d[bytes(key)] = bytes(value)
            self._dirty = True
            return True
        sec_type, index, key = data
        if key is None:
            values = self._lists.get(sec_type)
            return values[index] if values is not None and index < len(values) else None
        d = self._keys.get(sec_type)
        return d.get(bytes(key)) if d is not None else None


SECRETS = Secrets()          # one radio, one store - head and node share it


def keys_path(base_dir):
    """Where the keys are kept: next to the app's data when that is on the internal flash, else on /flash."""
    return (base_dir if not base_dir.startswith("/sd") else "/flash") + "/ble_keys.json"
