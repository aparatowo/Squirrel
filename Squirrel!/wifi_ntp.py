# wifi_ntp.py - device adapter: saved Wi-Fi network + NTP time (used by TimeSyncService)
#
# The networks are the app's own list (Settings -> Connections -> WiFi networks, wifi_profiles.py) - one list, visible
# and editable.  The network M5Burner leaves in UIFlow's NVS ("uiflow": ssid0 / pswd0) is not used (2026-10-20: a
# hidden second place that was hard to understand).  If UIFlow already connected at start-up the connection is reused.

import time
from boot_log import log

_NTP_HOSTS = ("pool.ntp.org", "time.google.com", "time.cloudflare.com")
_NTP_TIMEOUT_S = 2
_NO_AP_GRACE_MS = 6000     # a hotspot that is switched on may need a scan or two to show up
_SCANS = 2                 # a scan now and then misses a network that is there: two, their results merged


class WifiNtpClient:
    def __init__(self, radio, fallback_ssid=None, fallback_password="", profiles=None):
        self._radio = radio
        self._profiles = profiles              # function returning [(ssid, password)]; default: the saved networks file
        self._fb_ssid = fallback_ssid          # values, or functions returning them (read live)
        self._fb_password = fallback_password
        self._wlan = None
        self._t_begin = 0

    def _config_credentials(self):
        """The WIFI_SSID / WIFI_PASSWORD fallback from config.txt, or None."""
        ssid = self._fb_ssid() if callable(self._fb_ssid) else self._fb_ssid
        if not ssid:
            return None
        pswd = self._fb_password() if callable(self._fb_password) else self._fb_password
        return (ssid, pswd)

    def candidates(self):
        """Every network the device could join: [(ssid, password, source)], most preferred first.

        The networks saved in Settings -> WiFi networks, then the config.txt fallback of older versions
        (adopt_fallback() moves it into the saved ones at start-up).
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
        fallback = self._config_credentials()
        if fallback:
            found.append((fallback[0], fallback[1], "config"))
        unique, seen = [], set()
        for item in found:
            if item[0] not in seen:
                seen.add(item[0])
                unique.append(item)
        return unique

    def plan(self):
        """Scan, and put every known network in the order to try it: [(ssid, password, source, rssi or None)] - those
        in range strongest first, then the ones no scan saw (hidden, or missed).  Raises LookupError when no network is
        known at all.  The scans block for a few seconds."""
        known = self.candidates()
        if not known:
            raise LookupError("no saved WiFi network")
        import network
        self._wlan = network.WLAN(network.STA_IF)
        if not self._wlan.active():
            self._wlan.active(True)
        results = []
        for _ in range(_SCANS):
            try:
                results += self._wlan.scan()
            except Exception as e:
                log(f"[WIFI] Scan failed ({e})")
        from wifi_profiles import plan_networks
        order = plan_networks(results, known)
        in_range = [s for s, _p, _src, rssi in order if rssi is not None]
        log(f"[WIFI] {len(in_range)} of {len(known)} known network(s) in range ({len(results)} seen): "
            f"{', '.join(in_range) or '-'}; trying {len(order)}")
        return order

    def begin(self, ssid, pswd):
        import network
        self._wlan = network.WLAN(network.STA_IF)
        if not self._wlan.active():
            self._wlan.active(True)
        if not self._wlan.isconnected():
            try:
                self._wlan.disconnect()              # a previous network that did not answer
            except Exception:
                pass
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
