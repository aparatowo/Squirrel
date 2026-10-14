# ble/peers.py - who is who in the Bluetooth sync: this device's slot and, on the head, its nodes (ble.json)
#
#   {"slot": 0, "nodes": [{"addr": "240ac4fa13de", "type": 0, "name": "Squirrel! T-Watch", "slot": 1,
#                          "synced": 1760259600, "events": 1760250000}]}
# slot: this device's (0 = the head, or a device that never joined one); a node gets its slot from the head when it
# joins.  On the head, each node's statistics and routine log are kept apart in focus/peers/<slot>/ (never added to
# the head's own).  Kept on the flash, next to config.txt - not on a removable card.
import json
import os

MAX_SLOT = 6


class Peers:
    def __init__(self, path, peers_dir):
        self._path = path
        self._dir = peers_dir
        self.slot = 0
        self.nodes = []
        try:
            with open(path) as f:
                data = json.loads(f.read())
            self.slot = int(data.get("slot", 0))
            self.nodes = [n for n in data.get("nodes", []) if isinstance(n, dict) and "addr" in n]
        except (OSError, ValueError, AttributeError):
            pass

    def save(self):
        try:
            with open(self._path, "w") as f:
                f.write(json.dumps({"slot": self.slot, "nodes": self.nodes}))
        except OSError as e:
            print("[BLE] cannot save %s: %s" % (self._path, e))

    # ---- the head's nodes
    def find(self, addr):
        for n in self.nodes:
            if n["addr"] == addr:
                return n
        return None

    def add(self, addr, addr_type, name):
        """A new node (or the one already known): returns its entry, with a free slot."""
        node = self.find(addr)
        if node is not None:
            return node
        used = {n["slot"] for n in self.nodes}
        free = [s for s in range(1, MAX_SLOT + 1) if s not in used]
        if not free:
            raise ValueError("no free slot (at most %d devices)" % MAX_SLOT)
        node = {"addr": addr, "type": addr_type, "name": name, "slot": free[0], "synced": 0, "events": 0}
        self.nodes.append(node)
        self.save()
        return node

    def remove(self, addr):
        self.nodes = [n for n in self.nodes if n["addr"] != addr]
        self.save()

    def name_of(self, slot):
        for n in self.nodes:
            if n["slot"] == slot:
                return n["name"]
        return None

    # ---- what the nodes reported
    def _folder(self, slot):
        path = "%s/%d" % (self._dir, slot)
        parts = path.split("/")
        for n in range(2, len(parts) + 1):                # every folder on the way (focus/ may not exist yet)
            try:
                os.mkdir("/".join(parts[:n]))
            except OSError:
                pass
        return path

    def save_stats(self, slot, stats):
        """The node's statistics as it sent them (the last 60 days): {"day": {"kind": n}}."""
        days = {}
        for s in stats:
            days.setdefault(s["day"], {})[s["k"]] = s["n"]
        with open(self._folder(slot) + "/stats.json", "w") as f:
            f.write(json.dumps(days))

    def stats(self, slot):
        try:
            with open("%s/%d/stats.json" % (self._dir, slot)) as f:
                return json.loads(f.read())
        except (OSError, ValueError):
            return {}

    def add_events(self, slot, events):
        with open(self._folder(slot) + "/events.txt", "a") as f:
            for e in events:
                f.write("%d,%d,%s\n" % (e["r"], e["at"], e["res"]))
