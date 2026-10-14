# ble/auto.py - automatic Bluetooth sync every BLE_AUTO_SYNC_MIN minutes (0: only on demand)
#
# The sessions are aligned to the clock - the minutes of the day divisible by the period (every 60: 10:00, 11:00 ...) -
# so the devices meet without talking first; their clocks agree because every sync sets the worse one.
#   a node (the watch):    from the slot on it waits for the head for NODE_WINDOW_S; it is an alarm source (alarms.py),
#                          so a watch in deep sleep wakes for it
#   the head (Cardputer):  HEAD_DELAY_S after the slot it syncs every device (a node needs those seconds to wake up)
# A slot is skipped while the radio is taken (a Bluetooth screen, the Wi-Fi time sync) or a node needs pairing - that
# takes a code typed on the head, so it is done from Settings -> Bluetooth.  The setting is one of the head's synced
# settings (ble/protocol.SYNCED_KEYS): the watch follows the Cardputer.
import time
from boot_log import log

NODE_WINDOW_S = 90
HEAD_DELAY_S = 20
_LATE_S = 60                    # a slot found this late (a slow wake-up) is still taken
_CHECK_MS = 1000


def period_s(cfg):
    try:
        return max(0, int(cfg.get("BLE_AUTO_SYNC_MIN"))) * 60
    except Exception:
        return 0


def slot_of(now, period):
    """The start (epoch, local) of the slot `now` is in."""
    t = time.localtime(now)
    midnight = now - (t[3] * 3600 + t[4] * 60 + t[5])
    return midnight + (now - midnight) // period * period


class AutoSync:
    def __init__(self, app, cfg, role):
        self._app = app
        self._cfg = cfg
        self.role = role                 # "head" / "node"
        self._done = None                # the slot last taken
        self._checked = 0
        self._head = None
        self._node = None

    @property
    def busy(self):
        return self._head is not None or self._node is not None

    # ---- the watch: when to wake up (alarms.py source)
    def events(self, now, until):
        period = period_s(self._cfg)
        if not period or self.role != "node":
            return []
        from i18n import _
        label = _("Bluetooth sync")
        out = []
        at = slot_of(now, period) + period
        while at <= until and len(out) < 8:
            out.append((at, label))
            at += period
        return out

    # ---- the service
    def tick(self):
        if self._head is not None:
            self._tick_head()
            return
        if self._node is not None:
            self._tick_node()
            return
        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, self._checked) < _CHECK_MS:
            return
        self._checked = now_ms
        period = period_s(self._cfg)
        if not period:
            return
        now = time.time()
        if time.localtime(now)[0] < 2024:
            return                                        # no time yet: the slots mean nothing
        slot = slot_of(now, period)
        start = slot + (HEAD_DELAY_S if self.role == "head" else 0)
        if slot == self._done or not start <= now < start + _LATE_S or self._radio_taken():
            return
        self._done = slot
        try:
            if self.role == "head":
                self._start_head()
            else:
                self._start_node(slot + NODE_WINDOW_S - now)
        except Exception as e:
            log(f"[BLE] auto sync: {type(e).__name__}: {e}")
            self._finish()

    def _radio_taken(self):
        app = self._app
        return bool(getattr(app.radio, "ble_in_use", False)) or app._radio_in_use()

    def _start_head(self):
        from ble.node_data import for_app
        # by name, as the app's feature screens are: ble/central.py is in the head's firmware only (features.toml:
        # ble_hub), and build_firmware.py rejects a plain import of it on a node
        BleHead = __import__("ble.central", None, None, ("BleHead",)).BleHead
        data, peers = for_app(self._app)
        if not peers.nodes:
            return
        log("[BLE] auto sync (head)")
        self._app.radio.ble_in_use = True
        self._head = BleHead(data, peers, log=log)
        self._head.sync()

    def _tick_head(self):
        head = self._head
        head.tick()
        if head.need_code:                                 # pairing needs the user: not in the background
            log("[BLE] auto sync: a device wants pairing - use Settings -> Bluetooth")
            head.stop()
        if not head.busy:
            log("[BLE] auto sync: %s" % head.status)
            self._finish()

    def _start_node(self, window_s):
        from ble.node_data import for_app, device_name
        from ble.peripheral import BleNode
        data, _peers = for_app(self._app)
        log("[BLE] auto sync (node, %d s)" % window_s)
        self._app.radio.ble_in_use = True
        self._node = BleNode(data, name=device_name(), log=log)
        self._node.start(max(10, int(window_s)))

    def _tick_node(self):
        node = self._node
        node.tick()
        if node.state == "off":
            self._finish()

    def cancel(self):
        """A Bluetooth screen takes the radio: the session running in the background ends now."""
        if self.busy:
            log("[BLE] auto sync: stopped (a Bluetooth screen opened)")
            self._finish()

    def _finish(self):
        for part in (self._head, self._node):
            if part is not None:
                try:
                    part.stop()
                except Exception:
                    pass
        self._head = self._node = None
        self._app.radio.ble_in_use = False
