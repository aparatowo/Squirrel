# ble/peripheral.py - a node of the Bluetooth sync: the Squirrel! GATT server (docs/implementation/en/bluetooth.md 3, data-format.md 4)
#
# Built on MicroPython's own `bluetooth` module (no asyncio, no aioble): the IRQ handler only queues what happened -
# copying a written value at once, the next write would overwrite it - and tick() does the work, from the main loop.
# Small values are plain characteristics (INFO, TIME, the revision of each data set); everything else goes through
# CONTROL: LIST / GET / PUT / DELETE in frames, answers as notifications (protocol.frames()).
#
#   node = BleNode(NodeData(...), name="Squirrel! T-Watch")
#   node.start(window_s=120)      # radio on, advertising; stops by itself when nobody comes / after the session
#   node.tick()                   # often (the sync screen does it); node.state: "off" / "advertising" / "connected"
#   node.stop()                   # radio off
from ble import protocol as P
from ble.secrets import SECRETS

_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3
_IRQ_MTU_EXCHANGED = 21
_IRQ_ENCRYPTION_UPDATE = 28
_IRQ_PASSKEY_ACTION = 31
_PASSKEY_DISPLAY = 3            # this device shows the code, the other one types it in
_PASSKEY_NUMCMP = 4
_IO_DISPLAY_ONLY = 0            # what this device can do for pairing: show a code

_F_READ = 0x0002
_F_WRITE = 0x0008
_F_NOTIFY = 0x0010
_F_WRITE_AUTH = 0x2000          # writes only over an authenticated (paired with a code) link


def _setting(name, default):
    try:
        import nuts
        return getattr(nuts, name, default)
    except ImportError:
        return default


def link_pairing():
    """Pairing and encryption of the link itself (nuts.BLE_LINK_PAIRING; off: see there)."""
    return _setting("BLE_LINK_PAIRING", False)


def require_pairing():
    """Only a head paired with a code is served (ble/auth.py)."""
    return _setting("BLE_REQUIRE_PAIRING", True)


def _write_flag():
    return _F_WRITE | (_F_WRITE_AUTH if link_pairing() and require_pairing() else 0)

SET_SETTINGS = P.SET_SETTINGS
_IDLE_MS = 60000                # connected but nothing asked for this long: the session is over
_CODE_MS = 100000               # ... while the code shown is being typed on the head (it waits 90 s)
_LINGER_MS = 15000              # after the head disconnects: still visible this long (its second round), within the window
_ADV_INTERVAL_US = 250000
_NOTIFY_BURST = 8               # notifications per tick (the stack's buffers are few)
_WRITE_ROOM = 512

_CHARS = (                      # (uuid, flags, name)
    (P.INFO_UUID, _F_READ, "info"),
    (P.TIME_UUID, _F_READ | 0, "time"),                    # write flags added in start() (_write_flag)
    (P.SETTINGS_UUID, _F_READ, "settings"),
    (P.ROUTINES_UUID, _F_READ, "routines"),
    (P.TODO_UUID, _F_READ, "todo"),
    (P.STATS_UUID, _F_READ, "stats"),
    (P.STATUS_UUID, _F_READ | _F_NOTIFY, "status"),
    (P.CONTROL_UUID, _F_NOTIFY, "control"),
    (P.NOTES_UUID, _F_READ, "notes"),
    (P.EVENTS_UUID, _F_READ, "events"),
)
_SET_CHAR = {P.SET_ROUTINES: "routines", P.SET_TODO: "todo", P.SET_STATS: "stats", P.SET_NOTES: "notes",
             P.SET_EVENTS: "events", SET_SETTINGS: "settings"}
_INLINE = (P.SET_STATS, P.SET_EVENTS)


def radio_gc(on):
    """While the radio works the garbage is collected only here, in the main loop (radio_gc_tick), never by an
    allocation: the copies the IRQ handler must make would otherwise run the collector on the Bluetooth stack's small
    stack when the heap is full - the Cardputer (~140 KB of heap, ~23 KB of it taken by the stack) reset doing that,
    reproducibly; with the collector off and collected from the main loop the same sync went through (2026-10-13).
    Later the real cause of most of the resets turned out to be ble/central.py keeping the IRQ's own tuple; whether
    the collector in the IRQ is safe after that fix is still to be tried (docs/implementation/en/backlog.md, A)."""
    import gc
    try:
        gc.collect()
        gc.disable() if on else gc.enable()
    except AttributeError:                            # CPython (the tests)
        pass


def radio_gc_tick():
    import gc
    try:
        gc.collect()
    except AttributeError:
        pass


def _ticks():
    import time
    return time.ticks_ms()


def _since(a, b):
    import time
    return time.ticks_diff(a, b)


class BleNode:
    def __init__(self, data, ble=None, name="Squirrel!", log=None, now_ms=None):
        self.data = data
        self._ble = ble
        self._name = name
        self._log = log or (lambda text: None)
        self._now = now_ms or _ticks
        self.state = "off"
        self.conn = None
        self.was_connected = False        # someone connected during this window (even if nothing was asked)
        self.room = 20                    # MTU - 3; the default MTU is 23 until the central asks for more
        self.handles = {}
        self.counts = {"get": 0, "put": 0, "delete": 0, "list": 0, "errors": 0}
        self.last_error = None
        self._queue = []                  # events from the IRQ handler
        self._out = []                    # notifications waiting to go
        self._parts = P.Reassembler()
        self._deadline = None
        self._last_activity = 0
        self._time_at = None
        self.passkey = None               # the code to show while a head / phone pairs with this device
        self.secure = False               # link pairing only: the link is encrypted and authenticated
        self.authorized = False           # the head proved in this session that it is paired (ble/auth.py)
        self._pairing = None              # (head nonce, node nonce, code) while a pairing waits for the code
        self._challenge = None

    # ---------------------------------------------------------------------------------------------- radio
    def start(self, window_s=120):
        if self._ble is None:
            import bluetooth
            self._ble = bluetooth.BLE()
        ble = self._ble
        radio_gc(True)                                    # see radio_gc(): no collection from inside the IRQ handler
        self.authorized, self._pairing, self._challenge, self.passkey = False, None, None, None
        ble.active(True)
        try:
            ble.config(gap_name=self._name[:24], mtu=256)
        except Exception:
            pass
        if link_pairing():                                # pairing: LE Secure Connections, a code this device shows
            try:
                ble.config(bond=True, le_secure=True, mitm=True, io=_IO_DISPLAY_ONLY)
            except Exception as e:
                self._log("[BLE] pairing options refused: %s" % e)
        ble.irq(self._irq)
        import bluetooth
        writable = _write_flag()
        chars = tuple((bluetooth.UUID(u), f | (writable if n in ("time", "control") else 0)) for u, f, n in _CHARS)
        handles = ble.gatts_register_services(((bluetooth.UUID(P.SERVICE_UUID), chars),))[0]
        self.handles = {name: h for (_u, _f, name), h in zip(_CHARS, handles)}
        for name in ("time", "control"):
            ble.gatts_set_buffer(self.handles[name], _WRITE_ROOM)
        ble.gatts_write(self.handles["info"], P.pack_info(self.data.info()))
        self._refresh_time()
        self._refresh_revisions()
        self._deadline = (self._now(), window_s * 1000)
        self._advertise()
        self._log("[BLE] node up, advertising for %d s" % window_s)

    def _advertise(self):
        uuid = P.uuid_bytes(P.SERVICE_UUID)
        adv = b"\x02\x01\x06" + bytes((len(uuid) + 1, 0x07)) + uuid
        name = self._name.encode()[:29]
        resp = bytes((len(name) + 1, 0x09)) + name
        self._ble.gap_advertise(_ADV_INTERVAL_US, adv_data=adv, resp_data=resp)
        self.state = "advertising"

    def stop(self):
        if self._ble is None or self.state == "off":
            self.state = "off"
            return
        try:
            self._ble.gap_advertise(None)
            if self.conn is not None:
                self._ble.gap_disconnect(self.conn)
        except Exception:
            pass
        _settle()                                       # let the stack's timers run out before it is torn down
        try:
            self._ble.active(False)
        except Exception:
            pass
        self.state, self.conn = "off", None
        self._out, self._queue = [], []
        self.authorized, self._pairing, self._challenge, self.passkey = False, None, None, None
        radio_gc(False)
        self._parts.reset()
        self._log("[BLE] node off (%s)" % ", ".join("%s %d" % kv for kv in sorted(self.counts.items())))

    @property
    def busy(self):
        return self.state != "off"

    def seconds_left(self):
        """Of the advertising window (None when connected / off)."""
        if self.state != "advertising" or self._deadline is None:
            return None
        start, length = self._deadline
        return max(0, (length - _since(self._now(), start)) // 1000)

    # ---------------------------------------------------------------------------------------------- IRQ
    def _irq(self, event, data):
        # Runs in the Bluetooth stack's task, on its small stack: copy and go (see ble/central.py)
        if SECRETS.handles(event):
            return SECRETS.irq(event, data)
        if event == _IRQ_GATTS_WRITE:
            conn, handle = data[0], data[1]
            self._queue.append((event, conn, handle, bytes(self._ble.gatts_read(handle))))
        elif event == _IRQ_CENTRAL_CONNECT or event == _IRQ_CENTRAL_DISCONNECT:
            self._queue.append((event, data[0], None, None))      # ints are copies already; the address is not kept
        elif event == _IRQ_MTU_EXCHANGED:
            self._queue.append((event, data[0], data[1], None))
        elif event == _IRQ_PASSKEY_ACTION:
            self._queue.append((event, data[0], data[1], data[2]))   # conn, action, passkey
        elif event == _IRQ_ENCRYPTION_UPDATE:
            self._queue.append((event, data[0], (data[1], data[2], data[3]), None))   # encrypted, authenticated, bonded

    # ---------------------------------------------------------------------------------------------- the work
    def tick(self):
        """-> True when something changed that a screen shows."""
        if self.state == "off":
            return False
        changed = False
        while self._queue:
            event, conn, handle, value = self._queue.pop(0)
            changed = True
            self._last_activity = self._now()
            if event == _IRQ_CENTRAL_CONNECT:
                self.authorized, self._pairing, self._challenge, self.passkey = False, None, None, None
                self.conn, self.state = conn, "connected"
                self.was_connected = True
                self._log("[BLE] connected")
            elif event == _IRQ_CENTRAL_DISCONNECT:
                self.conn = None
                self.authorized, self._pairing, self._challenge, self.passkey = False, None, None, None
                self._parts.reset()
                self._out = []
                self._log("[BLE] disconnected")
                start, length = self._deadline
                left = length - _since(self._now(), start)
                if left <= 0:
                    self.stop()
                    return True
                self._deadline = (self._now(), min(left, _LINGER_MS))    # the head may come back for a second round
                self._advertise()
            elif event == _IRQ_MTU_EXCHANGED:
                self.room = max(20, handle - 3)
            elif event == _IRQ_PASSKEY_ACTION:
                self._on_passkey(conn, handle)
            elif event == _IRQ_ENCRYPTION_UPDATE:
                encrypted, authenticated, bonded = handle
                self.secure = bool(encrypted and authenticated)
                self.passkey = None
                self._log("[BLE] link %s%s" % ("secure" if self.secure else "NOT authenticated",
                                               ", bonded" if bonded else ""))
            elif event == _IRQ_GATTS_WRITE:
                self._on_write(handle, value)
        SECRETS.flush()
        radio_gc_tick()
        if self.state == "connected":
            self._flush()
            t = self._now()
            if self._time_at is None or _since(t, self._time_at) >= 1000:
                self._refresh_time()
            if _since(t, self._last_activity) > (_CODE_MS if self._pairing else _IDLE_MS):
                self._log("[BLE] the head said nothing for %d s" % (_IDLE_MS // 1000))
                self.stop()
                changed = True
        elif self.state == "advertising":
            start, length = self._deadline
            if _since(self._now(), start) > length:
                self._log("[BLE] window closed" if self.was_connected else "[BLE] nobody came")
                self.stop()
                changed = True
        return changed

    def _on_passkey(self, conn, action):
        """Pairing asks for a code: this device makes one up and shows it (the screen reads self.passkey)."""
        if action == _PASSKEY_DISPLAY:
            import os
            code = int.from_bytes(os.urandom(4), "little") % 900000 + 100000
            self.passkey = "%06d" % code
            self._log("[BLE] pairing: showing the code")
            self._ble.gap_passkey(conn, action, code)
        elif action == _PASSKEY_NUMCMP:
            self._ble.gap_passkey(conn, action, 0)        # no buttons to confirm with: refuse
        else:
            self._log("[BLE] pairing method %d not supported" % action)

    def _flush(self):
        sent = 0
        while self._out and sent < _NOTIFY_BURST:
            try:
                self._ble.gatts_notify(self.conn, self.handles["control"], self._out[0])
            except OSError:
                return                                # out of buffers: the rest next tick
            self._out.pop(0)
            sent += 1

    def _refresh_time(self):
        self._ble.gatts_write(self.handles["time"], P.pack_time(self.data.time()))
        self._time_at = self._now()

    def _refresh_revisions(self):
        import struct
        for which, name in _SET_CHAR.items():
            try:
                if which == SET_SETTINGS:
                    rev = 0
                    for b in P.pack_settings(self.data.settings()):
                        rev = (rev * 31 + b) & 0xFFFFFFFF
                else:
                    rev = self.data.revision(self.data.records(which))
            except Exception:
                rev = 0
            self._ble.gatts_write(self.handles[name], struct.pack("<I", rev))

    def _send(self, code, which, rid, payload=b""):
        self._out.extend(P.frames(code, which, rid, payload, self.room))

    def _error(self, which, rid, code, why):
        self.counts["errors"] += 1
        self.last_error = why
        self._log("[BLE] error %d (%s) for set %d id %d" % (code, why, which, rid))
        self._out.append(P.error_frame(which, rid, code))

    def _allowed(self):
        return self.authorized or not require_pairing() or link_pairing()

    def _on_write(self, handle, value):
        if handle == self.handles.get("time"):
            if not self._allowed():
                self.counts["errors"] += 1
                self.last_error = "time: not paired"
                return
            try:
                self.data.set_time(P.unpack_time(value))
                self._refresh_time()
                self._log("[BLE] clock set by the head")
            except Exception as e:
                self.counts["errors"] += 1
                self.last_error = "time: %s" % e
            return
        if handle != self.handles.get("control"):
            return
        try:
            code, which, rid, part, last, data = P.parse_frame(value)
        except ValueError as e:
            self._error(0, 0, P.ERR_BAD_DATA, str(e))
            return
        try:
            if code in P.AUTH_COMMANDS:
                self._on_auth(code, data)
                return
            if not self._allowed():
                raise ValueError(P.ERR_NOT_AUTH)
            if code == P.CMD_LIST:
                self._on_list(which, data)
            elif code == P.CMD_GET:
                self._on_get(which, rid)
            elif code == P.CMD_PUT:
                payload = self._parts.feed(code, which, rid, part, last, data)
                if payload is not None:
                    self._on_put(which, rid, payload)
            elif code == P.CMD_DELETE:
                if self.data.delete(which, rid):
                    self.counts["delete"] += 1
                    self._out.append(P.frame(P.ANS_ACK, which, rid))
                    self._refresh_revisions()
                else:
                    self._error(which, rid, P.ERR_NO_RECORD, "no such record")
            else:
                self._error(which, rid, P.ERR_BAD_DATA, "command %d" % code)
        except ValueError as e:
            arg = e.args[0] if e.args else None
            self._error(which, rid, arg if isinstance(arg, int) else P.ERR_BAD_DATA, str(e))
        except Exception as e:                        # a failing file system must not take the radio down
            self._error(which, rid, P.ERR_BAD_DATA, "%s: %s" % (type(e).__name__, e))

    def _on_auth(self, code, data):
        """Pairing with a code and the proof of every session (ble/auth.py)."""
        from ble import auth as A
        store = getattr(self.data, "auth", None)
        if code == P.CMD_AUTH_HELLO:
            nonce, code_text = A.random_bytes(A.NONCE_LEN), A.new_code()
            self._pairing = (bytes(data[:A.NONCE_LEN]), nonce, code_text)
            self.passkey = code_text                       # the screen shows it; the user types it on the head
            self._log("[BLE] pairing: showing the code")
            self._send(P.ANS_DATA, P.SET_INFO, 0, nonce)
        elif code == P.CMD_AUTH_CONFIRM:
            pending, self._pairing, self.passkey = self._pairing, None, None
            if pending is None or store is None:
                raise ValueError(P.ERR_BAD_DATA)
            key = A.pair_key(pending[2], pending[0], pending[1])
            if not A.same(bytes(data), A.confirm_proof(key, pending[1])):
                self._log("[BLE] pairing: wrong code")
                raise ValueError(P.ERR_BAD_CODE)
            store.set("head", key)
            self._log("[BLE] paired with the head")
            self._out.append(P.frame(P.ANS_ACK, P.SET_INFO, 0))
        elif code == P.CMD_AUTH_CHALLENGE:
            self._challenge = A.random_bytes(A.NONCE_LEN)
            self._send(P.ANS_DATA, P.SET_INFO, 0, self._challenge)
        else:
            key = store.get("head") if store is not None else None
            challenge, self._challenge = self._challenge, None
            if key is None or challenge is None or not A.same(bytes(data), A.session_proof(key, challenge)):
                raise ValueError(P.ERR_NOT_AUTH)
            self.authorized = True
            self._out.append(P.frame(P.ANS_ACK, P.SET_INFO, 0))

    def _on_list(self, which, data):
        self.counts["list"] += 1
        if which == SET_SETTINGS:
            raise ValueError(P.ERR_UNKNOWN_SET)
        records = self.data.records(which, since=P.unpack_since(data))
        rev = self.data.revision(records)
        payload = P.pack_inline_list(which, rev, records) if which in _INLINE else P.pack_list(rev, records)
        self._send(P.ANS_DATA, which, 0, payload)

    def _on_get(self, which, rid):
        self.counts["get"] += 1
        if which == SET_SETTINGS:
            self._send(P.ANS_DATA, which, 0, P.pack_settings(self.data.settings()))
            return
        r = self.data.get(which, rid)
        if r is None:
            self._error(which, rid, P.ERR_NO_RECORD, "no such record")
            return
        self._send(P.ANS_DATA, which, rid, P.pack_record(which, r))

    def _on_put(self, which, rid, payload):
        if which == P.SET_INFO:
            self.data.join(rid)
            self._ble.gatts_write(self.handles["info"], P.pack_info(self.data.info()))
            self._log("[BLE] joined the head as slot %d" % rid)
        elif which == SET_SETTINGS:
            applied, refused = self.data.apply_settings(P.unpack_settings(payload))
            self._log("[BLE] settings: %d applied, %d refused" % (applied, refused))
        else:
            r = P.unpack_record(which, payload)
            if r.get("id") != rid:
                raise ValueError(P.ERR_BAD_DATA)
            self.data.put(which, r)
        self.counts["put"] += 1
        self._out.append(P.frame(P.ANS_ACK, which, rid))
        self._refresh_revisions()


def _settle():
    """A moment between stopping the radio's work and switching it off: a NimBLE timer that fires after
    active(False) posts to a queue that is gone (a panic seen on the watch, esp_timer -> npl_freertos_eventq_put)."""
    import time
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(100)
