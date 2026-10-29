# time_sync.py - one-shot clock setting over Wi-Fi + NTP, as a background service
#
# States: idle -> scanning -> connecting -> syncing -> done | failed.  The main loop ticks it, so
# waiting for the network never blocks keys or the display (an NTP query itself blocks
# for at most its socket timeout, and the one network scan for a few seconds).  Whatever the outcome, the radios are switched off
# again afterwards (net.close()).  The clock is set in local time - the rest of the
# app treats the internal RTC as local time - and mirrored to a DS1302 if one answers.

import time
from boot_log import log
from timeutil import local_from_utc

_CONNECT_TIMEOUT_MS = 20000
_UNSEEN_TIMEOUT_MS = 8000          # a known network no scan saw (hidden, or missed): a shorter try
_NTP_RETRY_GAP_MS = 1500
_NTP_ATTEMPTS = 3


# The messages stay English here; the screen shows them with i18n.fill(message, MESSAGE_TEMPLATES).
MESSAGE_TEMPLATES = ("Looking for a network...", "no saved WiFi network", "WiFi scan failed: %s", "no saved network in range",
                     "WiFi start failed: %s", "Connecting...", "Getting time...", "connection failed",
                     "connection timeout (is the hotspot on?)", "NTP failed: %s", "clock write failed: %s",
                     "Synced %02d:%02d %02d-%02d-%04d", "wrong password", "network not found")


class TimeSyncService:
    def __init__(self, rtc, net, utc_offset_min=60, eu_dst=True):
        self._rtc = rtc
        self._net = net
        self._offset = utc_offset_min      # values, or functions returning them (read live)
        self._eu_dst = eu_dst
        self.state = "idle"
        self.message = ""
        self.ssid = ""
        self.reason = ""            # 'boot' or 'manual'
        self._t0 = 0                # when the sync started (what the screen counts from)
        self._t_connect = 0         # when the connection attempt started (the timeout counts from here)
        self._attempt = 0
        self._next_at = 0
        self._queue = []            # the networks still to try: [(ssid, password, source, rssi or None)]
        self._timeout = _CONNECT_TIMEOUT_MS
        self._seen = False          # the network being tried was in the scan
        self._problem = None        # what went wrong with a network that was in range: shown if every try fails

    @property
    def busy(self):
        return self.state in ("scanning", "connecting", "syncing")

    def elapsed_s(self):
        return time.ticks_diff(time.ticks_ms(), self._t0) // 1000 if self.busy else 0

    def start(self, reason=""):
        """Begin a sync.  Returns False if one is already running or cannot start."""
        if self.busy:
            return False
        self.reason = reason
        self.ssid = ""
        self.state = "scanning"
        self.message = "Looking for a network..."
        self._t0 = time.ticks_ms()
        self._attempt = 0
        log(f"[TIMESYNC] ({reason}) started")
        return True

    def tick(self):
        if self.state == "scanning":
            self._tick_scanning()
        elif self.state == "connecting":
            self._tick_connecting()
        elif self.state == "syncing":
            self._tick_syncing()

    def _tick_scanning(self):
        """Scan, then try the known networks one after another: those in range strongest first, then the rest
        (the scans block briefly)."""
        self._problem = None
        try:
            self._queue = self._net.plan()
        except LookupError as e:
            self._fail(str(e) or "no saved WiFi network")
            return
        except Exception as e:
            self._fail("WiFi scan failed: %s" % e)
            return
        self._next_network()

    def _next_network(self, problem=None):
        """Connect to the next network of the queue; when none is left, fail - with what went wrong with a network
        that was in range ("wrong password"), rather than with the last one tried ("not found")."""
        if problem and (self._seen or self._problem is None):
            self._problem = problem
        while self._queue:
            ssid, password, _source, rssi = self._queue.pop(0)
            self.ssid = ssid
            try:
                self._net.begin(ssid, password)
            except Exception as e:
                problem = "WiFi start failed: %s" % e
                continue
            self.state = "connecting"
            self.message = "Connecting..."
            self._t_connect = time.ticks_ms()
            self._seen = rssi is not None
            self._timeout = _CONNECT_TIMEOUT_MS if self._seen else _UNSEEN_TIMEOUT_MS
            log(f"[TIMESYNC] connecting to '{ssid}'" + ("" if rssi is not None else " (not seen by the scan)"))
            return
        self._fail(self._problem or "no saved network in range")

    def _tick_connecting(self):
        result = self._net.poll()
        if result == "connected":
            self.state = "syncing"
            self.message = "Getting time..."
            self._next_at = time.ticks_ms()
            return
        if result.startswith("failed"):
            problem = result[len("failed:"):].strip() or "connection failed"
        elif time.ticks_diff(time.ticks_ms(), self._t_connect) > self._timeout:
            problem = "connection timeout (is the hotspot on?)"
        else:
            return
        log(f"[TIMESYNC] '{self.ssid}': {problem}")
        self._next_network(problem)

    def _tick_syncing(self):
        now = time.ticks_ms()
        if time.ticks_diff(now, self._next_at) < 0:
            return
        try:
            utc = self._net.query_utc(self._attempt)
        except Exception as e:
            self._attempt += 1
            if self._attempt >= _NTP_ATTEMPTS:
                self._fail("NTP failed: %s" % e)
            else:
                self._next_at = time.ticks_add(now, _NTP_RETRY_GAP_MS)
            return
        offset = self._offset() if callable(self._offset) else self._offset
        eu_dst = self._eu_dst() if callable(self._eu_dst) else self._eu_dst
        local = local_from_utc(utc, offset, eu_dst)
        try:
            self._rtc.set_manual((local[0], local[1], local[2], local[3], local[4], local[5], local[6], 0))
        except Exception as e:
            self._fail("clock write failed: %s" % e)     # never leave the radios on
            return
        self._rtc.last_sync_source = "wifi"
        self.state = "done"
        self.message = "Synced %02d:%02d %02d-%02d-%04d" % (local[3], local[4], local[2], local[1], local[0])
        log(f"[TIMESYNC] {self.message} (UTC {utc[3]:02d}:{utc[4]:02d})")
        self._close_net()

    def _fail(self, text):
        self.state = "failed"
        self.message = text
        log(f"[TIMESYNC] Failed: {text}")
        self._close_net()

    def _close_net(self):
        try:
            self._net.close()
        except Exception as e:
            log(f"[TIMESYNC] Radio shutdown problem: {e}")
