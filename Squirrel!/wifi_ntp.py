# wifi_ntp.py - device adapter: saved Wi-Fi network + NTP time (used by TimeSyncService)
#
# UIFlow keeps the network entered in M5Burner in NVS namespace "uiflow"
# (keys ssid0 / pswd0), so no password ever has to be typed or stored by this app.
# If UIFlow already connected at start-up the existing connection is reused.

import time
from boot_log import log

_NTP_HOSTS = ("pool.ntp.org", "time.google.com", "time.cloudflare.com")
_NTP_TIMEOUT_S = 2
_NO_AP_GRACE_MS = 6000     # a hotspot that is switched on may need a scan or two to show up


class WifiNtpClient:
    def __init__(self, radio, fallback_ssid=None, fallback_password="", profiles=None):
        self._radio = radio
        self._profiles = profiles              # function returning [(ssid, password)]; default: the saved networks file
        self._fb_ssid = fallback_ssid          # values, or functions returning them (read live)
        self._fb_password = fallback_password
        self._wlan = None
        self._t_begin = 0

    def _system_credentials(self):
        """The network UIFlow keeps in NVS (entered in M5Burner), or None."""
        try:
            import esp32
            nvs = esp32.NVS("uiflow")
            ssid = nvs.get_str("ssid0")
            try:
                pswd = nvs.get_str("pswd0")
            except Exception:
                pswd = ""
            if ssid:
                return ssid, pswd
        except Exception as e:
            log(f"[WIFI] No saved UIFlow network: {e}")
        return None

    def _config_credentials(self):
        """The WIFI_SSID / WIFI_PASSWORD fallback from config.txt, or None."""
        ssid = self._fb_ssid() if callable(self._fb_ssid) else self._fb_ssid
        if not ssid:
            return None
        pswd = self._fb_password() if callable(self._fb_password) else self._fb_password
        return (ssid, pswd)

    def saved_credentials(self):
        """(ssid, password) from UIFlow's NVS, else the config fallback, else None."""
        return self._system_credentials() or self._config_credentials()

    def candidates(self):
        """Every network the device could join: [(ssid, password, source)], most preferred first.

        The networks saved in Settings -> WiFi networks come first, then UIFlow's own, then the
        config.txt fallback.  If one of them is ever missing the others still work.
        """
        found = []
        try:
            if self._profiles is not None:
                saved = self._profiles()
            else:
                import nuts
                from wifi_profiles import WifiProfiles
                saved = WifiProfiles(nuts.WIFI_PROFILES_FILE).all()
            for ssid, pswd in saved:
                found.append((ssid, pswd, "saved"))
        except Exception as e:
            log(f"[WIFI] Saved networks unavailable: {e}")
        system = self._system_credentials()
        if system:
            found.append((system[0], system[1], "system"))
        fallback = self._config_credentials()
        if fallback:
            found.append((fallback[0], fallback[1], "config"))
        unique, seen = [], set()
        for item in found:
            if item[0] not in seen:
                seen.add(item[0])
                unique.append(item)
        return unique

    def choose(self):
        """Scan and pick the known network with the strongest signal.

        Returns (ssid, password, source), or None when none of the known networks is in range.
        Raises LookupError when no network is known at all.  The scan blocks for a few seconds.
        Hidden networks are not found by a scan; if the scan itself fails the first known one is tried.
        """
        known = self.candidates()
        if not known:
            raise LookupError("no saved WiFi network")
        import network
        self._wlan = network.WLAN(network.STA_IF)
        if not self._wlan.active():
            self._wlan.active(True)
        try:
            results = self._wlan.scan()
        except Exception as e:
            log(f"[WIFI] Scan failed ({e}); trying '{known[0][0]}'")
            return known[0]
        from wifi_profiles import choose_network
        best = choose_network(results, known)
        if best is None:
            log(f"[WIFI] None of {len(known)} known network(s) in range ({len(results)} seen)")
        else:
            log(f"[WIFI] Chose '{best[0]}' ({best[2]}) out of {len(known)} known")
        return best

    def begin(self, ssid, pswd):
        import network
        self._wlan = network.WLAN(network.STA_IF)
        if not self._wlan.active():
            self._wlan.active(True)
        if not self._wlan.isconnected():
            self._wlan.connect(ssid, pswd)
        self._t_begin = time.ticks_ms()

    def poll(self):
        """'connected', 'connecting' or 'failed: <reason>' - never blocks."""
        if self._wlan.isconnected():
            return "connected"
        import network
        status = self._wlan.status()
        if status == getattr(network, "STAT_WRONG_PASSWORD", None):
            return "failed: wrong password"
        if (status == getattr(network, "STAT_NO_AP_FOUND", None)
                and time.ticks_diff(time.ticks_ms(), self._t_begin) > _NO_AP_GRACE_MS):
            return "failed: network not found"
        return "connecting"

    def query_utc(self, attempt=0):
        """One NTP query (one server per call, at most a couple of seconds).

        Returns (year, month, day, hour, minute, second) in UTC.
        """
        import ntptime
        try:
            ntptime.timeout = _NTP_TIMEOUT_S
        except Exception:
            pass
        ntptime.host = _NTP_HOSTS[attempt % len(_NTP_HOSTS)]
        return time.gmtime(ntptime.time())[:6]

    def close(self):
        self._radio.power_down("time sync finished")
