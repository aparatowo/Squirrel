# wifi_profiles.py - the WiFi networks saved from Settings -> WiFi networks
#
# Stored as JSON in nuts.WIFI_PROFILES_FILE: [{"ssid": "...", "password": "..."}, ...].
# The passwords are kept in plain text, in a file that only lives on the SD card.
# choose_network() picks, among the networks the device knows, the one with the strongest signal.

import json
import os
from boot_log import log

MAX_NETWORKS = 8
MAX_SSID = 32
MAX_PASSWORD = 63


def _scan_name(ssid):
    if isinstance(ssid, (bytes, bytearray)):
        try:
            return bytes(ssid).decode()
        except Exception:
            return ""
    return ssid or ""


def choose_network(scan_results, candidates):
    """The known network with the strongest signal, or None if none of them was seen.

    scan_results: what WLAN.scan() returns: (ssid, bssid, channel, rssi, authmode, hidden).
    candidates:   [(ssid, password, source)] in order of preference; on a tie the earlier one wins.
    """
    strongest = {}
    for entry in scan_results:
        name = _scan_name(entry[0])
        if name and (name not in strongest or entry[3] > strongest[name]):
            strongest[name] = entry[3]
    best = None
    best_rssi = None
    for candidate in candidates:
        rssi = strongest.get(candidate[0])
        if rssi is not None and (best_rssi is None or rssi > best_rssi):
            best, best_rssi = candidate, rssi
    return best


class WifiProfiles:
    def __init__(self, path):
        self._path = path
        self._items = []          # [[ssid, password], ...]
        self.load()

    def load(self):
        self._items = []
        try:
            with open(self._path, "r") as f:
                data = json.load(f)
        except OSError:
            return
        except Exception as e:
            log(f"[WIFI] Cannot read {self._path}: {e}")
            return
        if not isinstance(data, list):
            return
        for item in data:
            try:
                ssid, password = item["ssid"], item.get("password", "")
            except Exception:
                continue
            if isinstance(ssid, str) and ssid and isinstance(password, str) and len(self._items) < MAX_NETWORKS:
                self._items.append([ssid[:MAX_SSID], password[:MAX_PASSWORD]])

    def save(self):
        """tmp file + remove + rename (FAT cannot rename over an existing file)."""
        tmp = self._path + ".tmp"
        try:
            parent = self._path.rsplit("/", 1)[0]
            try:
                os.stat(parent)
            except OSError:
                os.mkdir(parent)
            with open(tmp, "w") as f:
                json.dump([{"ssid": s, "password": p} for s, p in self._items], f)
            try:
                os.remove(self._path)
            except OSError:
                pass
            os.rename(tmp, self._path)
            return True
        except Exception as e:
            log(f"[WIFI] Save failed: {e}")
            return False

    def all(self):
        return [(s, p) for s, p in self._items]

    def count(self):
        return len(self._items)

    def is_full(self):
        return len(self._items) >= MAX_NETWORKS

    def add(self, ssid, password):
        """Add a network, or replace the password of a known one.  False if the list is full."""
        for item in self._items:
            if item[0] == ssid:
                item[1] = password[:MAX_PASSWORD]
                return self.save()
        if self.is_full():
            return False
        self._items.append([ssid[:MAX_SSID], password[:MAX_PASSWORD]])
        return self.save()

    def update(self, index, ssid, password):
        self._items[index] = [ssid[:MAX_SSID], password[:MAX_PASSWORD]]
        seen, unique = set(), []
        for item in self._items:                     # renaming onto another saved network merges them
            if item[0] not in seen:
                seen.add(item[0])
                unique.append(item)
        self._items = unique
        return self.save()

    def delete(self, index):
        del self._items[index]
        return self.save()
