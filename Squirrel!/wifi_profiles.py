# wifi_profiles.py - the WiFi networks saved from Settings -> WiFi networks
#
# Stored as JSON in nuts.WIFI_PROFILES_FILE: [{"ssid": "...", "password": "..."}, ...].
# The passwords are kept in plain text, in a file that only lives on the SD card.
# plan_networks() puts the networks the device knows in the order to try them: those a scan saw, strongest first, then
# the others (a hidden network, or one the scan missed).  A name typed on the device matches the scan's whatever its
# case or spaces ("home wifi " finds "Home WiFi", "Home _5G" finds "Home_5G" - a slip seen on 2026-10-20), and
# the scan's own spelling is the one joined.

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


def _key(name):
    return "".join(name.split()).lower()            # no spaces at all, no case


def plan_networks(scan_results, candidates):
    """[(ssid, password, source, rssi or None)]: the candidates the scan saw (under the scan's spelling), strongest
    first, then the rest in their own order (rssi None).

    scan_results: what WLAN.scan() returns (from one scan or several): (ssid, bssid, channel, rssi, authmode, hidden).
    candidates:   [(ssid, password, source)] in order of preference; on a tie the earlier one wins."""
    seen = {}                                        # key -> (rssi, the scan's name)
    for entry in scan_results:
        name = _scan_name(entry[0])
        if name and (_key(name) not in seen or entry[3] > seen[_key(name)][0]):
            seen[_key(name)] = (entry[3], name)
    found, rest = [], []
    for n, (ssid, password, source) in enumerate(candidates):
        hit = seen.get(_key(ssid))
        if hit is None:
            rest.append((ssid, password, source, None))
        else:
            found.append((-hit[0], n, (hit[1], password, source, hit[0])))
    found.sort()
    return [item for _r, _n, item in found] + rest


def adopt_fallback(cfg, path):
    """The single "fallback network" of older versions (WIFI_SSID / WIFI_PASSWORD in config.txt) joins the saved
    networks, once: there is one list, scanned automatically.  Returns True when it was moved."""
    ssid = cfg.get("WIFI_SSID")
    if not ssid:
        return False
    profiles = WifiProfiles(path)
    if not any(_key(s) == _key(ssid) for s, _p in profiles.all()) and not profiles.add(ssid, cfg.get("WIFI_PASSWORD")):
        return False
    cfg.set("WIFI_SSID", "")
    cfg.set("WIFI_PASSWORD", "")
    log(f"[WIFI] the fallback network '{ssid}' moved to the saved networks")
    return True


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
